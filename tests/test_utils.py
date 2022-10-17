from cfbs.utils import canonify, merge_json, loads_bundlenames


def test_canonify():
    assert canonify("Hello CFEngine!") == "Hello_CFEngine_"
    assert canonify("/etc/os-release") == "_etc_os_release"
    assert canonify("my-example-module") == "my_example_module"


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
