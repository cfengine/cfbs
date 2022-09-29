from cfbs.utils import canonify, merge_json


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
