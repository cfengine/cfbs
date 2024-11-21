from cfbs.utils import (
    canonify,
    deduplicate_def_json,
    dict_diff,
    file_sha256,
    merge_json,
    loads_bundlenames,
    string_sha256,
)


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


def test_dict_diff():
    A = {"A": "a", "B": "b", "C": "c"}
    B = {"A": "a", "B": "c", "D": "d"}

    assert dict_diff(A, B) == (["C"], ["D"], [("B", "b", "c")])


def test_string_sha256():
    s = "cfbs/masterfiles/"
    checksum = "9e63d3266f80328fb6547b3462e81ab55b13f689d6b0944e242e2b3a0f3a32a3"

    assert string_sha256(s) == checksum


def test_file_sha256():
    file_path = "tests/sample/foo/main.cf"
    checksum = "da90bdfe7b5ee30e4d7871496e8434603315fb1b267660e2d49aee8ef47b246d"

    assert file_sha256(file_path) == checksum


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
