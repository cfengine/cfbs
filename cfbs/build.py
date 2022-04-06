import os
from cfbs.utils import (
    cp,
    merge_json,
    mkdir,
    pad_right,
    read_json,
    rm,
    sh,
    touch,
    user_error,
    write_json,
)
from cfbs.pretty import pretty_file


def init_out_folder():
    rm("out", missing_ok=True)
    mkdir("out")
    mkdir("out/masterfiles")
    mkdir("out/steps")


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
        if "classes" not in merged:
            merged["classes"] = {}
        if "services_autorun_bundles" not in merged["classes"]:
            merged["classes"]["services_autorun_bundles"] = ["any"]
        inputs = []
        for root, dirs, files in os.walk(src):
            for f in files:
                if f.endswith(".cf"):
                    inputs.append(os.path.join(dstarg, f))
                    cp(os.path.join(root, f), os.path.join(destination, dstarg, f))
                elif f == "def.json":
                    extra = read_json(os.path.join(root, f))
                    if extra:
                        merged = merge_json(merged, extra)
                else:
                    cp(os.path.join(root, f), os.path.join(destination, dstarg, f))
        if "inputs" in merged:
            merged["inputs"].extend(inputs)
        else:
            merged["inputs"] = inputs
        write_json(defjson, merged)
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
