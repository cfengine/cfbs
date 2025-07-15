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
        "allow-all-hosts": {
            "description": "Allows all hosts / IP addresses to connect and fetch policy.",
            "tags": ["management", "experimental"],
            "repo": "https://github.com/cfengine/modules",
            "by": "https://github.com/olehermanse",
            "version": "0.0.1",
            "commit": "85f9aec38783b5a4dac4777ffa9d17fde5054d14",
            "subdirectory": "management/allow-all-hosts",
            "steps": ["json def.json def.json"],
        }
    },
}


def test_validate_mock_index():
    config = MockConfig(deepcopy(INDEX))
    assert validate_config(config) == 0

    # Deleting top level keys:

    config = MockConfig(deepcopy(INDEX))
    del config["name"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["description"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["type"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]
    assert validate_config(config) == 1

    # Deleting parts of the module:

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["description"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["tags"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["repo"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["by"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["version"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["commit"]
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["subdirectory"]
    assert validate_config(config) == 0  # Optional field

    config = MockConfig(deepcopy(INDEX))
    del config["index"]["allow-all-hosts"]["steps"]
    assert validate_config(config) == 1

    # Mess with some of the values:

    config = MockConfig(deepcopy(INDEX))
    config["index"]["allow-all-hosts"]["description"] = None
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    config["index"]["allow-all-hosts"]["tags"] = {}
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    config["index"]["allow-all-hosts"]["repo"] = None
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["repo"] = ""
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    config["index"]["allow-all-hosts"]["by"] = None
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["by"] = ""
    assert validate_config(config) == 1

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["allow-all-hosts"]["version"]
    config["index"]["allow-all-hosts"]["version"] = None
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["version"] = ""
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["version"] = "blah"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["version"] = "1.2"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["version"] = "1.2."
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["version"] = "1.2.3.4"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["version"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["allow-all-hosts"]["commit"]
    config["index"]["allow-all-hosts"]["commit"] = None
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["commit"] = ""
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["commit"] = "abcd"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["commit"] = "1234"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["commit"] = "1.2.3"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["commit"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["allow-all-hosts"]["subdirectory"]
    config["index"]["allow-all-hosts"]["subdirectory"] = None
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["subdirectory"] = ""
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["subdirectory"] = " "
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["subdirectory"] = before + "/"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["subdirectory"] = "./"
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["subdirectory"] = "./" + before
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["subdirectory"] = before
    assert validate_config(config) == 0

    config = MockConfig(deepcopy(INDEX))
    before = config["index"]["allow-all-hosts"]["steps"]
    config["index"]["allow-all-hosts"]["steps"] = None
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ""
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = []
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = [""]
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = [" "]
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ["", " ", "\n"]
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ["copy"]  # Too few args
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ["copy a"]  # Too few args
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ["copy a b"]  # Correct
    assert validate_config(config) == 0
    config["index"]["allow-all-hosts"]["steps"] = ["copy abc def"]  # Correct
    assert validate_config(config) == 0
    config["index"]["allow-all-hosts"]["steps"] = ["run"]  # Too few args
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ["run script.sh"]  # Correct
    assert validate_config(config) == 0
    config["index"]["allow-all-hosts"]["steps"] = ["copy", "blah", "blah"]
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = ["blah blah blah"]
    assert validate_config(config) == 1
    config["index"]["allow-all-hosts"]["steps"] = before
    assert validate_config(config) == 0
