from collections import OrderedDict
from copy import deepcopy

from cfbs.validate import validate_config


# Only 2 interactions between validate_config and the config object:
# 1. Run warn_about_unknown_keys()
# 2. Run raw_data to get just the data for validation
class MockConfig(OrderedDict):
    @property
    def raw_data(self):
        return deepcopy(self)

    def warn_about_unknown_keys(self, raise_exceptions=False):
        pass


INDEX = {
    "name": "index",
    "description": "An example index of 1 module",
    "type": "index",
    "index": {
        "delete-files": {
            "description": "Allows you to specify a list of files you want deleted on hosts in your infrastructure. "
            + "When this module is deployed as part of your policy set, every time CFEngine runs, it will check if "
            + "those files exist, and delete them if they do.",
            "tags": ["supported", "management"],
            "repo": "https://github.com/nickanderson/cfengine-delete-files",
            "by": "https://github.com/nickanderson",
            "version": "2.0.0",
            "commit": "84cce7c5653b6a5f2b5a28ebb33c697ffc676dd4",
            "steps": [
                "copy delete-files.cf services/cfbs/modules/delete-files/delete-files.cf",
                "input delete-files/input.json def.json",
                "bundles delete_files:delete_files",
                "policy_files services/cfbs/modules/delete-files/delete-files.cf",
            ],
            "input": [
                {
                    "type": "list",
                    "variable": "files",
                    "namespace": "delete_files",
                    "bundle": "delete_files",
                    "label": "Files",
                    "subtype": [
                        {
                            "key": "path",
                            "type": "string",
                            "label": "Path",
                            "question": "Path to file",
                        },
                        {
                            "key": "why",
                            "type": "string",
                            "label": "Why",
                            "question": "Why should this file be deleted?",
                            "default": "Unknown",
                        },
                    ],
                    "while": "Specify another file you want deleted on your hosts?",
                }
            ],
        }
    },
}


def test_validate_mock_input_delete_fields():
    config = MockConfig(deepcopy(INDEX))
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["type"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["variable"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["namespace"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["bundle"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["label"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["while"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][0]["key"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][0]["type"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][0]["label"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][0]["question"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][1]["key"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][1]["type"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][1]["label"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["delete-files"]["input"][0]["subtype"][1]["question"]
    assert validate_config(config) == 1


def test_validate_mock_input_edit_fields():
    config = MockConfig(deepcopy(INDEX))
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["type"]
    config["index"]["delete-files"]["input"][0]["type"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["type"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["type"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["type"] = "   "
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["type"] = "blah"
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["type"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["variable"]
    config["index"]["delete-files"]["input"][0]["variable"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["variable"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["variable"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["variable"] = "  "
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["variable"] = "blah_variable_name"
    assert validate_config(config) == 0
    config["index"]["delete-files"]["input"][0]["variable"] = "1234"
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["variable"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["namespace"]
    config["index"]["delete-files"]["input"][0]["namespace"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["namespace"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["namespace"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["namespace"] = "  "
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["namespace"] = "blah_namespace"
    assert validate_config(config) == 0
    config["index"]["delete-files"]["input"][0]["namespace"] = "1234"
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["namespace"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["bundle"]
    config["index"]["delete-files"]["input"][0]["bundle"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["bundle"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["bundle"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["bundle"] = "  "
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["bundle"] = "blah_bundle"
    assert validate_config(config) == 0
    config["index"]["delete-files"]["input"][0]["bundle"] = "1234"
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["bundle"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["label"]
    config["index"]["delete-files"]["input"][0]["label"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["label"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["label"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["label"] = "  "
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["label"] = "A label"
    assert validate_config(config) == 0
    config["index"]["delete-files"]["input"][0]["label"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["subtype"][0]["key"]
    config["index"]["delete-files"]["input"][0]["subtype"][0]["key"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["key"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["key"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["key"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["subtype"][0]["type"]
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = "blah"
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["subtype"][0]["type"]
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = "string"
    assert validate_config(config) == 0
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = "list"
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["type"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["delete-files"]["input"][0]["subtype"][0]["question"]
    config["index"]["delete-files"]["input"][0]["subtype"][0]["question"] = None
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["question"] = ""
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0][
        "question"
    ] = "A question?"
    assert validate_config(config) == 0
    config["index"]["delete-files"]["input"][0]["subtype"][0]["question"] = []
    assert validate_config(config) == 1
    config["index"]["delete-files"]["input"][0]["subtype"][0]["question"] = before
    assert validate_config(config) == 0
