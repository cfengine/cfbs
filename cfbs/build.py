"""
Functions for performing the core part of 'cfbs build'

This module contains the code for performing the actual build,
converting a project into a ready to deploy policy set.
To achieve this, we iterate over all the build steps in all
the modules running the appropriate file and shell operations.

There are some preliminary parts of 'cfbs build' implemented
elsewhere, like validation and downloading modules.
"""

import json
import os
import logging as log
import shutil
import subprocess
from cfbs.augments import generate_augment
from cfbs.cfbs_config import CFBSConfig
from cfbs.utils import (
    CFBSUserError,
    cli_tool_present,
    cp,
    cp_dry_overwrites,
    deduplicate_def_json,
    file_diff_text,
    find,
    merge_json,
    mkdir,
    pad_right,
    read_json,
    rm,
    save_file,
    sh,
    strip_left,
    touch,
    CFBSExitError,
    write_json,
)
from cfbs.pretty import pretty, pretty_file
from cfbs.validate import (
    AVAILABLE_BUILD_STEPS,
    MAX_REPLACEMENTS,
    step_has_valid_arg_count,
    split_build_step,
    validate_build_step,
)


def init_out_folder():
    rm("out", missing_ok=True)
    mkdir("out")
    mkdir("out/masterfiles")
    mkdir("out/steps")


def _perform_replacement(n, a, b, filename):
    assert n and a and b and filename
    assert a not in b

    or_more = False
    if n.endswith("+"):
        n = n[0:-1]
        or_more = True
    n = int(n)
    try:
        with open(filename, "r") as f:
            content = f.read()
    except FileNotFoundError:
        raise CFBSExitError("No such file '%s' in replace build step" % (filename,))
    except:
        raise CFBSExitError(
            "Could not open/read '%s' in replace build step" % (filename,)
        )
    new_content = previous_content = content
    for i in range(0, n):
        previous_content = new_content
        new_content = previous_content.replace(a, b, 1)
        if new_content == previous_content:
            raise CFBSExitError(
                "replace build step could only replace '%s' in '%s' %s times, not %s times (required)"
                % (a, filename, i, n)
            )

    if or_more:
        for i in range(n, MAX_REPLACEMENTS):
            previous_content = new_content
            new_content = previous_content.replace(a, b, 1)
            if new_content == previous_content:
                break
    if a in new_content:
        raise CFBSExitError("too many occurences of '%s' in '%s'" % (a, filename))
    try:
        with open(filename, "w") as f:
            f.write(new_content)
    except:
        raise CFBSExitError("Failed to write to '%s'" % (filename,))


def _apply_masterfiles_patch(patch_path):
    if not cli_tool_present("patch"):
        raise CFBSUserError("Working with .patch files requires the 'patch' utility")

    if not os.path.isfile(patch_path):
        raise CFBSExitError("Patch at path '%s' not found" % patch_path)

    patch_path = os.path.relpath(patch_path, "out/masterfiles")

    # reasoning for used flags:
    # * `-t`: do not interactively ask the user for another path if the patch fails to apply due to the path not being found
    # * `-p0`: use paths in the form specified in the .patch files
    cmd = "patch -u -t -p0 -i" + patch_path
    # the cwd needs to be the base path of the relative paths specified in the .patch files
    # currently, the output of the patch command is displayed
    cp = subprocess.run(cmd, shell=True, cwd="out/masterfiles")

    if cp.returncode != 0:
        raise CFBSExitError("Failed to apply patch '%s'" % patch_path)


def _perform_copy_step(args, source, destination, prefix):
    src, dst = args
    if dst in [".", "./"]:
        dst = ""
    print("%s copy '%s' 'masterfiles/%s'" % (prefix, src, dst))
    src, dst = os.path.join(source, src), os.path.join(destination, dst)

    step_diffs_data = ""

    noop_overwrites_relpaths, modifying_overwrites_relpaths = cp_dry_overwrites(
        src, dst
    )
    for file_relpath in modifying_overwrites_relpaths:
        if os.path.isfile(src):
            fileA = src
        else:
            fileA = os.path.join(src, file_relpath)
        if os.path.isfile(dst):
            fileB = dst
        else:
            fileB = os.path.join(dst, file_relpath)
        file_diff_data = file_diff_text(fileA, fileB)
        step_diffs_data += file_diff_data
    if len(noop_overwrites_relpaths) > 0:
        warning_message = (
            "Identical file overwrites occured during copy.\n"
            + " Check your modules and their build steps to ascertain whether this is intentional.\n"
            + " In most cases, the cause is a file from a latter module already being provided by an earlier module (commonly stock masterfiles).\n"
            + " In that case, the file is best deleted from the latter module(s).\n"
            + " Identical overwrites count: %s\n" % len(noop_overwrites_relpaths)
        )
        # display affected files, without flooding the output
        if len(noop_overwrites_relpaths) < 20:
            for overwrite_noop in noop_overwrites_relpaths:
                warning_message += "  " + overwrite_noop + "\n"
        else:
            for overwrite_noop in noop_overwrites_relpaths[:9]:
                warning_message += "  " + overwrite_noop + "\n"
            warning_message += "   ...\n"
            for overwrite_noop in noop_overwrites_relpaths[-9:]:
                warning_message += "  " + overwrite_noop + "\n"
        # display all the messages as one warning
        log.warning(warning_message)
    cp(src, dst)

    return step_diffs_data


def _perform_run_step(args, source, prefix):
    shell_command = " ".join(args)
    print("%s run '%s'" % (prefix, shell_command))
    sh(shell_command, source)


def _perform_delete_step(args, source, prefix):
    files = [args] if type(args) is str else args
    assert len(files) > 0
    as_string = " ".join(["'%s'" % f for f in files])
    print("%s delete %s" % (prefix, as_string))
    for file in files:
        if not rm(os.path.join(source, file), True):
            print(
                "Warning: tried to delete '%s' but path did not exist."
                % os.path.join(source, file)
            )


def _perform_json_step(args, source, destination, prefix):
    src, dst = args
    if dst in [".", "./"]:
        dst = ""
    print("%s json '%s' 'masterfiles/%s'" % (prefix, src, dst))
    if not os.path.isfile(os.path.join(source, src)):
        raise CFBSExitError("'%s' is not a file" % src)
    src, dst = os.path.join(source, src), os.path.join(destination, dst)
    extras, original = read_json(src), read_json(dst)
    if not extras:
        print("Warning: '%s' looks empty, adding nothing" % os.path.basename(src))
    if original:
        merged = merge_json(original, extras)
        if os.path.basename(dst) == "def.json":
            merged = deduplicate_def_json(merged)
    else:
        merged = extras
    write_json(dst, merged)


def _perform_append_step(args, source, destination, prefix):
    src, dst = args
    if dst in [".", "./"]:
        dst = ""
    print("%s append '%s' 'masterfiles/%s'" % (prefix, src, dst))
    src, dst = os.path.join(source, src), os.path.join(destination, dst)
    if not os.path.exists(dst):
        touch(dst)
    assert os.path.isfile(dst)
    sh("cat '%s' >> '%s'" % (src, dst))


def _perform_directory_step(args, source, destination, prefix):
    src, dst = args
    if dst in [".", "./"]:
        dst = ""
    print("{} directory '{}' 'masterfiles/{}'".format(prefix, src, dst))
    dstarg = dst  # save this for adding .cf files to inputs
    src, dst = os.path.join(source, src), os.path.join(destination, dst)
    defjson = os.path.join(destination, "def.json")
    merged = read_json(defjson)
    if not merged:
        merged = {}
    for root, _, files in os.walk(src):
        for f in files:
            if f == "def.json":
                extra = read_json(os.path.join(root, f))
                if extra:
                    merged = merge_json(merged, extra)
                    merged = deduplicate_def_json(merged)
            else:
                s = os.path.join(root, f)
                d = os.path.join(destination, dstarg, root[len(src) :], f)
                log.debug("Copying '%s' to '%s'" % (s, d))
                cp(s, d)
    write_json(defjson, merged)


def _path_if_already_shipped(path, build_modules, destination):
    """If `path` is already inside a local module's directory that has its own
    "directory" build step shipping it to masterfiles, return the on-host path
    that step will produce. That step already copies the whole directory
    during this same build, so the caller doesn't need to (and shouldn't)
    copy the file itself - just point at where it will end up.
    """
    abs_path = os.path.abspath(path)
    for module in build_modules:
        module_name = module.get("name", "")
        if not (module_name.startswith("./") and module_name.endswith("/")):
            continue
        module_root = os.path.abspath(module_name)

        if os.path.commonpath([abs_path, module_root]) != module_root:
            # Only a module that contains the file can be the one shipping it.
            # Without this, we'd match some other module's directory step and
            # return a non-None "already shipped" path, suppressing the copy the
            # file actually needs.
            continue
        for step in module.get("steps", []):
            operation, args = split_build_step(step)
            if operation != "directory" or len(args) != 2:
                continue
            src, dst = args
            if src not in (".", "./"):
                continue
            rel = os.path.relpath(abs_path, module_root)
            dst = "" if dst in (".", "./") else dst
            dest = os.path.join(destination, dst, rel)
            return "$(sys.inputdir)/" + os.path.relpath(dest, destination)
    return None


def _localize_file_inputs(name, input_data, destination, build_modules):
    """Copy files referenced by "file" type input responses into the built
    masterfiles, so they're actually part of what gets deployed instead of
    only existing in the project directory. Rewrites the responses in place
    to the resulting on-host path.

    If a response is already shipped by another module's own "directory"
    build step (e.g. the project author set one up manually), that step's
    destination is used instead of making a redundant copy.

    Returns the masterfiles-relative destination path of every file that was
    localized, so callers can make sure those exact paths get synced by the
    policy update mechanism even if their extension isn't one of the ones
    normally recognized.
    """
    if not isinstance(input_data, list):
        return []

    module_dir_name = name[2:] if name.startswith("./") else name
    module_dir_name = os.path.basename(module_dir_name.rstrip("/"))

    localized_paths = []

    def _localize(rel_path):
        if not rel_path or not os.path.isfile(rel_path):
            return rel_path

        already_shipped = _path_if_already_shipped(rel_path, build_modules, destination)
        if already_shipped is not None:
            localized_paths.append(strip_left(already_shipped, "$(sys.inputdir)/"))
            return already_shipped

        rel_path = os.path.normpath(rel_path)
        in_module_dir = rel_path.split(os.sep)[0] == module_dir_name

        dest = os.path.join(
            destination,
            "services",
            "cfbs",
            "modules" if in_module_dir else "",
            rel_path,
        )
        abs_destination = os.path.abspath(destination)
        if (
            os.path.commonpath([os.path.abspath(dest), abs_destination])
            != abs_destination
        ):
            # rel_path contained a ".." segment, or was absolute (which
            # discards the destination prefix in os.path.join above) -
            # either way it would land outside the built masterfiles.
            raise CFBSExitError(
                "Input file response '%s' would be placed outside the "
                "built masterfiles - refusing to copy it" % rel_path
            )
        cp(rel_path, dest)
        dest_rel = os.path.relpath(dest, destination)
        localized_paths.append(dest_rel)
        return "$(sys.inputdir)/" + dest_rel

    for element in input_data:
        if not isinstance(element, dict) or element.get("type") != "file":
            continue
        response = element.get("response")
        if isinstance(response, list):
            element["response"] = [_localize(path) for path in response]
        else:
            element["response"] = _localize(response)

    return localized_paths


def _perform_input_step(args, name, destination, prefix, build_modules):
    src, dst = args
    if dst in [".", "./"]:
        dst = ""
    print("%s input '%s' 'masterfiles/%s'" % (prefix, src, dst))
    if src.startswith(name + "/"):
        log.warning(
            "Deprecated 'input' build step behavior - it should be: 'input ./input.json def.json'"
        )
        # We'll translate it to what it should be
        # TODO: Consider removing this behavior for cfbs 4?
        src = "." + src[len(name) :]
    src = os.path.join(name, src)
    dst = os.path.join(destination, dst)
    if not os.path.isfile(os.path.join(src)):
        log.warning(
            "Input data '%s' does not exist: Skipping build step."
            % os.path.basename(src)
        )
        return
    extras, original = read_json(src), read_json(dst)
    localized_paths = _localize_file_inputs(name, extras, destination, build_modules)
    extras = generate_augment(name, extras)
    log.debug("Generated augment: %s", pretty(extras))
    if not extras:
        raise CFBSExitError(
            "Input data '%s' is incomplete: Skipping build step."
            % os.path.basename(src)
        )
    if localized_paths:
        # Files brought in through "file" type inputs aren't necessarily
        # matched by the policy update's default `input_name_patterns`.
        # Rather than widening that extension-based matching for the whole
        # policy set, point at exactly these files, by their literal
        # relative path.
        relative_paths = [path.replace(os.sep, "/") for path in localized_paths]
        extras = merge_json(
            extras, {"vars": {"default:update_def.input_paths_extra": relative_paths}}
        )
    if original:
        log.debug("Original def.json: %s", pretty(original))
        merged = merge_json(original, extras)
        merged = deduplicate_def_json(merged)
    else:
        merged = extras
    log.debug("Merged def.json: %s", pretty(merged))
    write_json(dst, merged)


def _perform_policy_files_step(args, destination, prefix):
    files = []
    for file in args:
        if file.startswith("./"):
            file = file[2:]
        if file.endswith(".cf"):
            files.append(file)
        elif file.endswith("/"):
            cf_files = find("out/masterfiles/" + file, extension=".cf")
            files += (strip_left(f, "out/masterfiles/") for f in cf_files)
        else:
            raise CFBSExitError(
                "Unsupported filetype '%s' for build step 'policy_files': " % file
                + "Expected directory (*/) of policy file (*.cf)"
            )
    print("%s policy_files '%s'" % (prefix, "' '".join(files) if files else ""))
    augment = {"inputs": files}
    log.debug("Generated augment: %s" % pretty(augment))
    path = os.path.join(destination, "def.json")
    original = read_json(path)
    log.debug("Original def.json: %s" % pretty(original))
    if original:
        merged = merge_json(original, augment)
        merged = deduplicate_def_json(merged)
    else:
        merged = augment
    log.debug("Merged def.json: %s", pretty(merged))
    write_json(path, merged)


def _perform_bundles_step(args, prefix, destination):
    bundles = args
    print("%s bundles '%s'" % (prefix, "' '".join(bundles) if bundles else ""))
    augment = {"vars": {"control_common_bundlesequence_end": bundles}}
    log.debug("Generated augment: %s" % pretty(augment))
    path = os.path.join(destination, "def.json")
    original = read_json(path)
    log.debug("Original def.json: %s" % pretty(original))
    if original:
        merged = merge_json(original, augment)
        merged = deduplicate_def_json(merged)
    else:
        merged = augment
    log.debug("Merged def.json: %s", pretty(merged))
    write_json(path, merged)


def _perform_replace_step(module, i, args, name, destination, prefix):
    assert len(args) == 4
    print("%s replace '%s'" % (prefix, "' '".join(args)))
    # New build step so let's be a bit strict about validating it:
    validate_build_step(name, module, i, "replace", args, strict=True)
    n, a, b, file = args
    file = os.path.join(destination, file)
    _perform_replacement(n, a, b, file)


def _perform_replace_version_step(module, i, args, name, destination, prefix):
    assert len(args) == 3
    # New build step so let's be a bit strict about validating it:
    validate_build_step(name, module, i, "replace_version", args, strict=True)
    print("%s replace_version '%s'" % (prefix, "' '".join(args)))
    n = args[0]
    to_replace = args[1]
    filename = os.path.join(destination, args[2])
    version = module["version"]
    _perform_replacement(n, to_replace, version, filename)


def _perform_patch_step(module, i, args, name, source, prefix):
    assert len(args) == 1

    patch_relpath = args[0]
    print("%s patch '%s'" % (prefix, patch_relpath))
    # New build step so let's be a bit strict about validating it:
    validate_build_step(name, module, i, "patch", args, strict=True)

    patch_path = os.path.join(source, patch_relpath)

    _apply_masterfiles_patch(patch_path)


def perform_build(config: CFBSConfig, diffs_filename=None) -> int:
    if not config.get("build"):
        raise CFBSExitError("No 'build' key found in the configuration")

    # mini-validation
    for module in config["build"]:
        for step in module["steps"]:
            operation, args = split_build_step(step)

            if step.split() != [operation] + args:
                raise CFBSExitError(
                    "Incorrect whitespace in the `%s` build step - singular spaces are required"
                    % step
                )

            if operation not in AVAILABLE_BUILD_STEPS:
                raise CFBSExitError("Unknown build step operation: %s" % operation)

            expected = AVAILABLE_BUILD_STEPS[operation]
            actual = len(args)
            if not step_has_valid_arg_count(args, expected):
                if type(expected) is int:
                    raise CFBSExitError(
                        "The `%s` build step expects %d arguments, %d were given"
                        % (step, expected, actual)
                    )
                else:
                    expected = int(expected[0:-1])
                    raise CFBSExitError(
                        "The `%s` build step expects %d or more arguments, %d were given"
                        % (step, expected, actual)
                    )

    diffs_data = ""

    print("\nSteps:")
    max_length = config.longest_module_key_length("name")
    for module in config["build"]:
        for i, step in enumerate(module["steps"]):
            operation, args = split_build_step(step)
            name = module["name"]
            source = module["_directory"]
            destination = "out/masterfiles"

            counter = module["_counter"]
            prefix = "%03d %s :" % (counter, pad_right(name, max_length))

            if operation == "copy":
                step_diffs_data = _perform_copy_step(args, source, destination, prefix)
                diffs_data += step_diffs_data
            elif operation == "run":
                _perform_run_step(args, source, prefix)
            elif operation == "delete":
                _perform_delete_step(args, source, prefix)
            elif operation == "json":
                _perform_json_step(args, source, destination, prefix)
            elif operation == "append":
                _perform_append_step(args, source, destination, prefix)
            elif operation == "directory":
                _perform_directory_step(args, source, destination, prefix)
            elif operation == "input":
                _perform_input_step(args, name, destination, prefix, config["build"])
            elif operation == "policy_files":
                _perform_policy_files_step(args, destination, prefix)
            elif operation == "bundles":
                _perform_bundles_step(args, prefix, destination)
            elif operation == "replace":
                _perform_replace_step(module, i, args, name, destination, prefix)
            elif operation == "replace_version":
                _perform_replace_version_step(
                    module, i, args, name, destination, prefix
                )
            elif operation == "patch":
                _perform_patch_step(module, i, args, name, source, prefix)

    if diffs_filename is not None:
        try:
            print(
                "\nWriting diffs of non-identical file overwrites to '%s'..."
                % diffs_filename
            )
            save_file(diffs_filename, diffs_data)
        except IsADirectoryError:
            log.warning(
                "An existing directory was provided as the '--diffs' file path - writing the diffs file for the build failed - continuing build..."
            )

    assert os.path.isdir("./out/masterfiles/")
    shutil.copyfile("./cfbs.json", "./out/masterfiles/cfbs.json")
    if os.path.isfile("out/masterfiles/def.json"):
        try:
            pretty_file("out/masterfiles/def.json")
        except json.decoder.JSONDecodeError as e:
            raise CFBSExitError(
                "Error parsing JSON in 'out/masterfiles/def.json': %s" % e
            )
    print("")
    print("Generating tarball...")
    sh("( cd out/ && tar -czf masterfiles.tgz masterfiles )")
    print("\nBuild complete, ready to deploy 🐿")
    print(" -> Directory: out/masterfiles")
    print(" -> Tarball:   out/masterfiles.tgz")
    print("")
    print("To install on this machine: sudo cfbs install")
    print("To deploy on remote hub(s): cf-remote deploy")
    return 0
