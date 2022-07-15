from cfbs.utils import canonify


def test_canonify():
    assert canonify("Hello CFEngine!") == "Hello_CFEngine_"
    assert canonify("/etc/os-release") == "_etc_os_release"
    assert canonify("my-example-module") == "my_example_module"
