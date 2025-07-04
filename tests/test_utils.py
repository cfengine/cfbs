from collections import OrderedDict
import os

import pytest

from cfbs.utils import (
    are_paths_equal,
    canonify,
    deduplicate_def_json,
    deduplicate_list,
    dict_diff,
    dict_sorted_by_key,
    file_sha256,
    immediate_files,
    immediate_subdirectories,
    is_a_commit_hash,
    merge_json,
    loads_bundlenames,
    pad_left,
    pad_right,
    path_append,
    read_file,
    read_json,
    string_sha256,
    strip_left,
    strip_left_any,
    strip_right,
    strip_right_any,
)


def test_pad_left():
    s = "module_name"
    n = 20

    assert pad_left(s, n) == "         module_name"


def test_pad_right():
    s = "module_name"
    n = 20

    assert pad_right(s, n) == "module_name         "


def test_strip_right():
    s = "abab"

    assert strip_right(s, "ab") == "ab"
    assert strip_right(s, "a") == "abab"


def test_strip_left():
    s = "abab"

    assert strip_left(s, "ab") == "ab"
    assert strip_left(s, "b") == "abab"


def test_strip_right_any():
    assert strip_right_any("a.b.c", (".b", ".c")) == "a.b"
    assert strip_right_any("a.b.c", (".c", ".b")) == "a.b"

    assert strip_right_any("a.b.b", (".b", ".b")) == "a.b"


def test_strip_left_any():
    assert strip_left_any("a.b.c", ("a.", "b.")) == "b.c"
    assert strip_left_any("a.b.c", ("b.", "a.")) == "b.c"

    assert strip_left_any("a.a.b", ("a.", "a.")) == "a.b"


def test_read_file():
    file_path = "tests/sample/sample_dir/sample_file_1.txt"
    expected_str = "sample_string\n123"
    nonpath = "tests/sample/sample_dir/sample_file_doesnt_exist.txt"

    assert read_file(file_path) == expected_str
    assert read_file(nonpath) is None


def test_read_json():
    json_path = "tests/sample/sample_json.json"
    expected_dict = OrderedDict(
        [("a", 1), ("b", OrderedDict([("c", "value"), ("d", [2, "string"])]))]
    )

    assert read_json(json_path) == expected_dict

    assert read_json("tests/thisfiledoesntexist.json") is None
    assert read_json("tests/thisdirdoesntexist/file.json") is None

    with pytest.raises(SystemExit) as exc_info:
        read_json("tests/sample/sample_bad_syntax.json")
    assert exc_info.value.code == 1


def test_merge_json():
    original = {"classes": {"services_autorun": ["any"]}}
    extras = {
        "variables": {
            "cfbs:create_single_file.filename": {
                "value": "/tmp/create-single-file.txt",
                "comment": "Added by 'cfbs input'",
            }
        }
    }
    merged = merge_json(original, extras)
    assert "classes" in merged
    assert "services_autorun" in merged["classes"]
    assert merged["classes"]["services_autorun"] == ["any"]
    assert "variables" in merged
    assert "cfbs:create_single_file.filename" in merged["variables"]
    assert "value" in merged["variables"]["cfbs:create_single_file.filename"]
    assert (
        merged["variables"]["cfbs:create_single_file.filename"]["value"]
        == "/tmp/create-single-file.txt"
    )
    assert "comment" in merged["variables"]["cfbs:create_single_file.filename"]
    assert (
        merged["variables"]["cfbs:create_single_file.filename"]["comment"]
        == "Added by 'cfbs input'"
    )

    original = {
        "classes": {"services_autorun": ["any"]},
        "inputs": ["services/cfbs/bogus.cf"],
        "vars": {"control_common_bundlesequence_end": ["bogus"]},
    }
    extras = {
        "inputs": ["services/cfbs/doofus/doofus.cf", "services/cfbs/doofus/foo/foo.cf"]
    }
    merged = merge_json(original, extras)
    expected = {
        "classes": {"services_autorun": ["any"]},
        "inputs": [
            "services/cfbs/bogus.cf",
            "services/cfbs/doofus/doofus.cf",
            "services/cfbs/doofus/foo/foo.cf",
        ],
        "vars": {"control_common_bundlesequence_end": ["bogus"]},
    }
    assert merged == expected


def test_deduplicate_def_json():
    case = {
        "inputs": [
            "services/cfbs/inventory/company.cf",
            "services/cfbs/inventory/company.cf",
            "services/cfbs/inventory/company.cf",
        ]
    }
    expected = {"inputs": ["services/cfbs/inventory/company.cf"]}

    deduplicated = deduplicate_def_json(case)
    assert deduplicated == expected

    case = {
        "augments": [
            "/var/cfengine/augments/company.json",
            "/var/cfengine/augments/company.json",
        ],
        "variables": {
            "MyNamespace:my_bundle.Variable": {
                "value": {"tags": ["dont-dedupe", "dont-dedupe"]},
                "tags": ["inventory", "attribute_name=My Inventory", "inventory"],
            }
        },
    }
    expected = {
        "augments": ["/var/cfengine/augments/company.json"],
        "variables": {
            "MyNamespace:my_bundle.Variable": {
                "value": {"tags": ["dont-dedupe", "dont-dedupe"]},
                "tags": ["inventory", "attribute_name=My Inventory"],
            }
        },
    }

    deduplicated = deduplicate_def_json(case)
    assert deduplicated == expected

    case = {
        "classes": {
            "my-class": [
                "^(?!MISSING).*",
                "cfengine::",
                "^(?!MISSING).*",
                "cfengine::",
            ],
        },
        "vars": {"augments_inputs": ["dont-dedupe-for-now", "dont-dedupe-for-now"]},
    }
    expected = {
        "classes": {
            "my-class": [
                "^(?!MISSING).*",
                "cfengine::",
            ],
        },
        "vars": {"augments_inputs": ["dont-dedupe-for-now", "dont-dedupe-for-now"]},
    }

    deduplicated = deduplicate_def_json(case)
    assert deduplicated == expected

    case = {
        "classes": {
            "my-class": {
                "class_expressions": ["cfengine|linux::", "cfengine|linux::"],
                "comment": "Optional class description of class",
                "tags": ["tags", "tags"],
            },
        },
    }
    expected = {
        "classes": {
            "my-class": {
                "class_expressions": ["cfengine|linux::"],
                "comment": "Optional class description of class",
                "tags": ["tags"],
            },
        },
    }

    deduplicated = deduplicate_def_json(case)
    assert deduplicated == expected


def test_deduplicate_list():
    nums = [1, 2, 3, 3, 1, 4]

    assert deduplicate_list(nums) == [1, 2, 3, 4]

    assert deduplicate_list([1, 1, 2, 3]) == [1, 2, 3]
    assert deduplicate_list([1, 2, 3, 3]) == [1, 2, 3]
    assert deduplicate_list([1, 2, 3]) == [1, 2, 3]

    assert deduplicate_list([]) == []
    assert deduplicate_list([1]) == [1]
    assert deduplicate_list([1, 1, 1, 1, 1, 1, 1]) == [1]


def test_dict_sorted_by_key():
    d = {"b": 1, "c": 3, "a": 2}

    expected_dict = OrderedDict([("a", 2), ("b", 1), ("c", 3)])

    assert dict_sorted_by_key(d) == expected_dict

    assert dict_sorted_by_key({}) == OrderedDict([])
    assert dict_sorted_by_key({"a": 1}) == OrderedDict([("a", 1)])


def test_dict_diff():
    A = {"A": "a", "B": "b", "C": "c"}
    B = {"A": "a", "B": "c", "D": "d"}

    assert dict_diff(A, B) == (["C"], ["D"], [("B", "b", "c")])


def test_immediate_subdirectories():
    path = "tests/sample/sample_dir"
    expected = ["sample_subdir_A", "sample_subdir_B"]

    assert immediate_subdirectories(path) == expected


def test_immediate_files():
    path = "tests/sample/sample_dir"
    expected = ["sample_file_1.txt", "sample_file_2.txt"]

    assert immediate_files(path) == expected


def test_path_append():
    path = "tests/sample/sample_dir"

    assert path_append(path, "abc") == path + "/abc"
    assert path_append(path, None) == path


def test_are_paths_equal():
    path_a = "abc"
    path_b = "abc/..//abc/"

    assert are_paths_equal(path_a, path_b)

    assert are_paths_equal(".", os.getcwd())

    assert are_paths_equal("a", "b") is False
    assert are_paths_equal("a", "") is False


def test_string_sha256():
    s = "cfbs/masterfiles/"
    checksum = "9e63d3266f80328fb6547b3462e81ab55b13f689d6b0944e242e2b3a0f3a32a3"

    assert string_sha256(s) == checksum


def test_file_sha256():
    file_path = "tests/sample/foo/main.cf"
    checksum = "da90bdfe7b5ee30e4d7871496e8434603315fb1b267660e2d49aee8ef47b246d"

    assert file_sha256(file_path) == checksum


def test_is_a_commit_hash():
    assert is_a_commit_hash("304d123ac7ff50714a1eb57077acf159f923c941") is True
    sha256_hash = "98142d6fa7e2e5f0942b0a215c1c4b976e7ae2ee5edb61cef974f1ba6756cbbc"
    assert is_a_commit_hash(sha256_hash) is True
    # at least currently, commit cannot be a shortened hash
    assert is_a_commit_hash("4738c43") is False
    assert is_a_commit_hash("") is False


def test_canonify():
    assert canonify("Hello CFEngine!") == "Hello_CFEngine_"
    assert canonify("/etc/os-release") == "_etc_os_release"
    assert canonify("my-example-module") == "my_example_module"


def test_loads_bundlenames_single_bundle():
    policy = """bundle agent bogus
{
  reports:
      "Hello World";
}
"""
    bundles = loads_bundlenames(policy)
    assert len(bundles) == 1
    assert bundles[0] == "bogus"


def test_loads_bundlenames_multiple_bundles():
    policy = """bundle\tagent bogus {
  reports:
      "Bogus!";
}

bundle agent doofus
{
  reports:
      "Doofus!";
}
"""
    bundles = loads_bundlenames(policy)
    assert len(bundles) == 2
    assert bundles[0] == "bogus"
    assert bundles[1] == "doofus"
