import os
import copy

from cfbs.build import _localize_file_inputs


def test_localize_file_inputs_copies_single_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    with open("deploy.sh", "w") as f:
        f.write("echo hi\n")

    input_data = [
        {
            "type": "file",
            "variable": "script",
            "response": "deploy.sh",
        }
    ]

    _localize_file_inputs("run-a-script", input_data, "out/masterfiles", [])

    expected_dest = "out/masterfiles/services/cfbs/deploy.sh"
    assert os.path.isfile(expected_dest)
    assert input_data[0]["response"] == "$(sys.inputdir)/services/cfbs/deploy.sh"


def test_localize_file_inputs_copies_list_of_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("run-scripts-module")
    with open("one.sh", "w") as f:
        f.write("echo one\n")
    with open("run-scripts-module/two.sh", "w") as f:
        f.write("echo two\n")

    input_data = [
        {
            "type": "file",
            "variable": "scripts",
            "response": ["one.sh", "run-scripts-module/two.sh"],
        }
    ]

    _localize_file_inputs("run-scripts-module", input_data, "out/masterfiles", [])

    assert input_data[0]["response"] == [
        "$(sys.inputdir)/services/cfbs/one.sh",
        "$(sys.inputdir)/services/cfbs/modules/run-scripts-module/two.sh",
    ]
    assert os.path.isfile("out/masterfiles/services/cfbs/one.sh")
    assert os.path.isfile(
        "out/masterfiles/services/cfbs/modules/run-scripts-module/two.sh"
    )


def test_localize_file_inputs_strips_local_module_prefix_with_dot_slash(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("run-a-script")
    with open("run-a-script/deploy.sh", "w") as f:
        f.write("echo hi\n")

    input_data = [
        {
            "type": "file",
            "variable": "script",
            "response": "./run-a-script/deploy.sh",
        }
    ]

    _localize_file_inputs("./run-a-script", input_data, "out/masterfiles", [])

    assert input_data[0]["response"] == (
        "$(sys.inputdir)/services/cfbs/modules/run-a-script/deploy.sh"
    )
    assert os.path.isfile(
        "out/masterfiles/services/cfbs/modules/run-a-script/deploy.sh"
    )


def test_localize_file_inputs_strips_local_module_prefix(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("run-a-script")
    with open("run-a-script/deploy.sh", "w") as f:
        f.write("echo hi\n")

    input_data = [
        {"type": "file", "variable": "script", "response": "run-a-script/deploy.sh"}
    ]

    _localize_file_inputs("./run-a-script", input_data, "out/masterfiles", [])

    assert os.path.isfile(
        "out/masterfiles/services/cfbs/modules/run-a-script/deploy.sh"
    )


def test_localize_file_inputs_ignores_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")

    input_data = [
        {"type": "file", "variable": "script", "response": "does-not-exist.sh"}
    ]
    before = copy.deepcopy(input_data)

    _localize_file_inputs("run-a-script", input_data, "out/masterfiles", [])

    assert input_data == before


def test_localize_file_inputs_ignores_non_file_types(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")

    input_data = [
        {"type": "string", "variable": "filename", "response": "/tmp/foo.txt"}
    ]
    before = copy.deepcopy(input_data)

    _localize_file_inputs("some-module", input_data, "out/masterfiles", [])

    assert input_data == before


def test_localize_file_inputs_skips_copy_when_already_shipped(tmp_path, monkeypatch):
    """When the referenced file is already inside a module directory that has
    its own "directory" build step, that step's destination should be used
    instead of also copying the file into services/cfbs/modules/<module>/.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("./run-scripts/input_files")
    with open("./run-scripts/input_files/deploy.sh", "w") as f:
        f.write("echo hi\n")

    build_modules = [
        {
            "name": "./run-scripts/input_files/",
            "steps": ["directory ./ services/cfbs/run-scripts/input_files/"],
        }
    ]
    input_data = [
        {
            "type": "file",
            "variable": "script",
            "response": "./run-scripts/input_files/deploy.sh",
        }
    ]

    _localize_file_inputs("run-scripts", input_data, "out/masterfiles", build_modules)

    assert input_data[0]["response"] == (
        "$(sys.inputdir)/services/cfbs/run-scripts/input_files/deploy.sh"
    )
    # The file was NOT additionally copied to the bespoke destination:
    assert not os.path.isfile(
        "out/masterfiles/services/cfbs/modules/run-scripts/deploy.sh"
    )


def test_localize_file_inputs_ignores_non_directory_steps(tmp_path, monkeypatch):
    """A registered module whose steps don't include a "directory ./ ..."
    step (e.g. it only copies a single file) shouldn't be mistaken for
    already shipping the referenced file - the bespoke copy should still
    happen.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("./run-scripts")
    with open("./run-scripts/deploy.sh", "w") as f:
        f.write("echo hi\n")

    build_modules = [
        {
            "name": "./run-scripts/",
            "steps": ["copy deploy.sh services/cfbs/run-scripts/deploy.sh"],
        }
    ]
    input_data = [
        {"type": "file", "variable": "script", "response": "run-scripts/deploy.sh"}
    ]

    _localize_file_inputs("run-scripts", input_data, "out/masterfiles", build_modules)

    assert input_data[0]["response"] == (
        "$(sys.inputdir)/services/cfbs/modules/run-scripts/deploy.sh"
    )
    assert os.path.isfile("out/masterfiles/services/cfbs/modules/run-scripts/deploy.sh")
