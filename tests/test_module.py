from cfbs.module import Module


def test_init():
    """Test initializing with and without version"""

    module = Module("groups@0.1.2")
    assert module.name == "groups"
    assert module.version == "0.1.2"

    module = Module("groups")
    assert module.name == "groups"
    assert module.version is None


def test_type_constraints():
    """Make sure type constraints are only enforced for Module specific attributes"""

    module = Module("groups")

    try:
        module.description = "Manage local groups"
        success = True
    except ValueError as e:
        print(e)
        success = False
    assert success

    try:
        module.description = 123
        success = False
    except ValueError as e:
        print(e)
        success = True

    try:
        module.steps = ["alice", "bob", "charlie"]
        success = True
    except ValueError as e:
        print(e)
        success = False
    assert success

    try:
        module.steps = "alice"
        success = False
    except ValueError as e:
        print(e)
        success = True
    assert success

    try:
        module.steps = ["alice", "bob", 123]
        success = False
    except ValueError as e:
        print(e)
        success = True
    assert success

    try:
        module.x = 123
        success = True
    except ValueError as e:
        print(e)
        success = False
    assert success


def test_attribute_defaults():
    """Make sure only Module specific attributes default to None"""

    module = Module("groups")

    try:
        assert module.commit is None
        success = True
    except AttributeError as e:
        print(e)
        success = False
    assert success

    try:
        print(module.x)
        success = False
    except AttributeError as e:
        print(e)
        success = True
    assert success


def test_mutual_exclusion():
    """Test that mutual exclusion constraint works"""

    module = Module("groups")

    try:
        module.repo = "my_repo"
        success = True
    except ValueError as e:
        print(e)
        success = False
    assert success

    try:
        module.path = "my_path"
        success = False
    except ValueError as e:
        print(e)
        success = True
    assert success
