"""
Functions for performing the core part of 'cfbs build'

This module contains the code for performing the actual build,
converting a project into a ready to deploy policy set.
To achieve this, we iterate over all the build steps in all
the modules running the appropriate file and shell operations.

There are some preliminary parts of 'cfbs build' implemented
elsewhere, like validation and downloading modules.
"""

import os
import logging as log
import shutil
from cfbs.utils import (
    canonify,
    cp,
    deduplicate_def_json,
    find,
    merge_json,
    mkdir,
    pad_right,
    read_json,
    rm,
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


def _generate_augment(module_name, input_data):
    """
    Generate augment from input data.

    :param module_name: name of module
    :param input_data: input data
    :return: generated augment or None if input data is incomplete
    """
    if not isinstance(input_data, list):
        return None

    augment = {"variables": {}}

    for variable in input_data:
        if not isinstance(variable, dict) or any(
            key not in variable for key in ("variable", "response")
        ):
            return None

        name = variable["variable"]
        namespace = variable.get("namespace", "cfbs")
        bundle = variable.get("bundle", canonify(module_name))
        value = variable["response"]
        comment = variable.get("comment", "Added by 'cfbs input'")

        augment["variables"]["%s:%s.%s" % (namespace, bundle, name)] = {
            "value": value,
            "comment": comment,
        }

    return augment


def _perform_replace_step(n, a, b, filename):
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


def _perform_build_step(module, i, step, max_length):
    operation, args = split_build_step(step)
    name = module["name"]
    source = module["_directory"]
    counter = module["_counter"]
    destination = "out/masterfiles"

    prefix = "%03d %s :" % (counter, pad_right(name, max_length))

    assert operation in AVAILABLE_BUILD_STEPS  # Should already be validated
    if operation == "copy":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("%s copy '%s' 'masterfiles/%s'" % (prefix, src, dst))
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        cp(src, dst)
    elif operation == "run":
        shell_command = " ".join(args)
        print("%s run '%s'" % (prefix, shell_command))
        sh(shell_command, source)
    elif operation == "delete":
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
    elif operation == "json":
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
    elif operation == "append":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("%s append '%s' 'masterfiles/%s'" % (prefix, src, dst))
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        if not os.path.exists(dst):
            touch(dst)
        assert os.path.isfile(dst)
        sh("cat '%s' >> '%s'" % (src, dst))
    elif operation == "directory":
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
    elif operation == "input":
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
        extras = _generate_augment(name, extras)
        log.debug("Generated augment: %s", pretty(extras))
        if not extras:
            raise CFBSExitError(
                "Input data '%s' is incomplete: Skipping build step."
                % os.path.basename(src)
            )
        if original:
            log.debug("Original def.json: %s", pretty(original))
            merged = merge_json(original, extras)
            merged = deduplicate_def_json(merged)
        else:
            merged = extras
        log.debug("Merged def.json: %s", pretty(merged))
        write_json(dst, merged)
    elif operation == "policy_files":
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
                    "Unsupported filetype '%s' for build step '%s': "
                    % (file, operation)
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
    elif operation == "bundles":
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
    elif operation == "replace":
        assert len(args) == 4
        print("%s replace '%s'" % (prefix, "' '".join(args)))
        # New build step so let's be a bit strict about validating it:
        validate_build_step(name, module, i, operation, args, strict=True)
        n, a, b, file = args
        file = os.path.join(destination, file)
        _perform_replace_step(n, a, b, file)
    elif operation == "replace_version":
        assert len(args) == 3
        # New build step so let's be a bit strict about validating it:
        validate_build_step(name, module, i, operation, args, strict=True)
        print("%s replace_version '%s'" % (prefix, "' '".join(args)))
        n = args[0]
        to_replace = args[1]
        filename = os.path.join(destination, args[2])
        version = module["version"]
        _perform_replace_step(n, to_replace, version, filename)


def perform_build(config) -> int:
    if not config.get("build"):
        raise CFBSExitError("No 'build' key found in the configuration")

    # mini-validation
    for module in config.get("build", []):
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

    print("\nSteps:")
    module_name_length = config.longest_module_key_length("name")
    for module in config.get("build", []):
        for i, step in enumerate(module["steps"]):
            _perform_build_step(module, i, step, module_name_length)
    assert os.path.isdir("./out/masterfiles/")
    shutil.copyfile("./cfbs.json", "./out/masterfiles/cfbs.json")
    if os.path.isfile("out/masterfiles/def.json"):
        pretty_file("out/masterfiles/def.json")
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
