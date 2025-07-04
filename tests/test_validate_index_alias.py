import os

from cfbs.pretty import pretty
from cfbs.validate import validate_config
from cfbs.cfbs_config import CFBSConfig

INDEX_ALIAS_VALID = {
    "name": "index",
    "description": "An example index of 1 module",
    "type": "index",
    "index": {
        "test-alias": {
            "alias": "test-target",
        },
        "test-target": {
            "description": "Allows all hosts / IP addresses to connect and fetch policy.",
            "tags": ["management", "experimental"],
            "repo": "https://github.com/cfengine/modules",
            "by": "https://github.com/olehermanse",
            "version": "0.0.1",
            "commit": "85f9aec38783b5a4dac4777ffa9d17fde5054d14",
            "subdirectory": "management/allow-all-hosts",
            "steps": ["json def.json def.json"],
        },
    },
}

INDEX_ALIAS_INVALID = {
    "name": "index",
    "description": "An example index of 1 module",
    "type": "index",
    "index": {
        "test-alias": {
            "alias": "test-target",
        }
    },
}


def test_valid_index_with_alias():
    filename = "./tmp-cfbs.json"
    with open(filename, "w") as f:
        f.write(pretty(INDEX_ALIAS_VALID))
    config = CFBSConfig(filename)
    r = validate_config(config)
    del config
    os.remove(filename)
    assert r == 0


def test_invalid_index_with_alias():
    filename = "./tmp-cfbs.json"
    with open(filename, "w") as f:
        f.write(pretty(INDEX_ALIAS_INVALID))
    config = CFBSConfig(filename)
    r = validate_config(config)
    del config
    os.remove(filename)
    assert r != 0
