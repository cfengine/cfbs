import os
import logging as log
from cfbs.utils import (
    canonify,
    cp,
    find,
    merge_json,
    mkdir,
    pad_right,
    read_json,
    rm,
    sh,
    strip_left,
    touch,
    user_error,
    write_json,
)
from cfbs.pretty import pretty, pretty_file


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


def _perform_build_step(module, step, max_length):
    step = step.split(" ")
    operation, args = step[0], step[1:]
    source = module["_directory"]
    counter = module["_counter"]
    destination = "out/masterfiles"

    prefix = "%03d %s :" % (counter, pad_right(module["name"], max_length))

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
            rm(os.path.join(source, file))
    elif operation == "json":
        src, dst = args
        if dst in [".", "./"]:
            dst = ""
        print("%s json '%s' 'masterfiles/%s'" % (prefix, src, dst))
        if not os.path.isfile(os.path.join(source, src)):
            user_error("'%s' is not a file" % src)
        src, dst = os.path.join(source, src), os.path.join(destination, dst)
        extras, original = read_json(src), read_json(dst)
        if not extras:
            print("Warning: '%s' looks empty, adding nothing" % os.path.basename(src))
        if original:
            merged = merge_json(original, extras)
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
        if "subdirectory" in module:
            src = os.path.join(module["subdirectory"], src)
        dst = os.path.join(destination, dst)
        if not os.path.isfile(os.path.join(src)):
            log.warning(
                "Input data '%s' does not exist: Skipping build step."
                % os.path.basename(src)
            )
            return
        extras, original = read_json(src), read_json(dst)
        extras = _generate_augment(module["name"], extras)
        log.debug("Generated augment: %s", pretty(extras))
        if not extras:
            user_error(
                "Input data '%s' is incomplete: Skipping build step."
                % os.path.basename(src)
            )
        if original:
            log.debug("Original def.json: %s", pretty(original))
            merged = merge_json(original, extras)
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
                user_error(
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
        merged = merge_json(original, augment) if original else augment
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
        merged = merge_json(original, augment) if original else augment
        log.debug("Merged def.json: %s", pretty(merged))
        write_json(path, merged)
    else:
        user_error("Unknown build step operation: %s" % operation)


def perform_build_steps(config) -> int:
    print("\nSteps:")
    module_name_length = config.longest_module_name()
    for module in config["build"]:
        for step in module["steps"]:
            _perform_build_step(module, step, module_name_length)
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
