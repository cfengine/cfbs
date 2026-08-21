import os
import copy
import json

import pytest

from cfbs.build import _localize_file_inputs, _perform_input_step
from cfbs.utils import CFBSExitError


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

    localized_paths = _localize_file_inputs(
        "run-a-script", input_data, "out/masterfiles", []
    )

    expected_dest = "out/masterfiles/services/cfbs/deploy.sh"
    assert os.path.isfile(expected_dest)
    assert input_data[0]["response"] == "$(sys.inputdir)/services/cfbs/deploy.sh"
    assert localized_paths == ["services/cfbs/deploy.sh"]


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

    localized_paths = _localize_file_inputs(
        "run-scripts-module", input_data, "out/masterfiles", []
    )

    assert input_data[0]["response"] == [
        "$(sys.inputdir)/services/cfbs/one.sh",
        "$(sys.inputdir)/services/cfbs/modules/run-scripts-module/two.sh",
    ]
    assert os.path.isfile("out/masterfiles/services/cfbs/one.sh")
    assert os.path.isfile(
        "out/masterfiles/services/cfbs/modules/run-scripts-module/two.sh"
    )
    assert localized_paths == [
        "services/cfbs/one.sh",
        "services/cfbs/modules/run-scripts-module/two.sh",
    ]


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


def test_localize_file_inputs_rejects_path_traversal(tmp_path, monkeypatch):
    """An absolute (or '..'-laden) response would otherwise let os.path.join
    discard the destination prefix, placing the file outside the built
    masterfiles entirely - refuse it instead of writing there."""
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    outside = tmp_path.parent / ("cfbs-traversal-test-%d.txt" % os.getpid())
    outside.write_text("pwned\n")
    try:
        input_data = [{"type": "file", "variable": "script", "response": str(outside)}]

        with pytest.raises(CFBSExitError):
            _localize_file_inputs("some-module", input_data, "out/masterfiles", [])

        assert not os.path.exists("out/masterfiles/services/cfbs/" + outside.name)
    finally:
        try:
            outside.unlink()
        except OSError:
            pass


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


def test_perform_input_step_adds_input_paths_extra_for_localized_files(
    tmp_path, monkeypatch
):
    """A "file" type input should make the build add its exact destination
    path to `default:update_def.input_paths_extra`, so the policy update
    mechanism syncs it even if its extension isn't in the default
    `input_name_patterns` list.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("run-a-script")
    with open("deploy.sh", "w") as f:
        f.write("echo hi\n")
    with open("run-a-script/input.json", "w") as f:
        json.dump([{"type": "file", "variable": "script", "response": "deploy.sh"}], f)

    _perform_input_step(
        ["./input.json", "def.json"], "run-a-script", "out/masterfiles", "+", []
    )

    with open("out/masterfiles/def.json") as f:
        result = json.load(f)

    expected_path = "services/cfbs/deploy.sh"
    assert result["vars"]["default:update_def.input_paths_extra"] == [expected_path]


def test_perform_input_step_skips_input_paths_extra_for_non_file_inputs(
    tmp_path, monkeypatch
):
    """A build with only "string"-type inputs has nothing to localize, so no
    `input_paths_extra` augment should be generated at all.
    """
    monkeypatch.chdir(tmp_path)
    os.makedirs("out/masterfiles")
    os.makedirs("some-module")
    with open("some-module/input.json", "w") as f:
        json.dump([{"type": "string", "variable": "greeting", "response": "hello"}], f)

    _perform_input_step(
        ["./input.json", "def.json"], "some-module", "out/masterfiles", "+", []
    )

    with open("out/masterfiles/def.json") as f:
        result = json.load(f)

    assert "vars" not in result
