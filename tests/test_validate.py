import pytest

from cfbs.utils import CFBSValidationError
from cfbs.validate import input_data_matches_spec, validate_module_name_content


def test_validate_module_name_content():
    validate_module_name_content("regular-name")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("Uppercase-name")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("underscore_but_not_local")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("name with spaces")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("-leading-hyphen")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content(
            "module-name-too-longggggggggggggggggggggggggggggggggggggggggggggg"
        )

    validate_module_name_content("./local_module.cf")
    validate_module_name_content("./local_module_directory/")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("not_local_module.cf")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("./_leading_underscore/")
    validate_module_name_content("./good-extension.json")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("./bad-extension.zip")

    validate_module_name_content("./123 Illeg@l!/legal-name.cf")


def test_input_data_matches_spec_string():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        }
    ]
    data = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    # The response is what the user adds, it is ignored when comparing:
    assert input_data_matches_spec(spec, data)

    # Input data without a response conforms as well:
    assert input_data_matches_spec(spec, spec)


def test_input_data_matches_spec_list():
    spec = [
        {
            "type": "list",
            "variable": "files",
            "label": "Files",
            "subtype": [
                {
                    "key": "name",
                    "type": "string",
                    "label": "Name",
                    "question": "What file should this module create?",
                },
                {
                    "key": "content",
                    "type": "string",
                    "label": "Content",
                    "question": "What content should this file have?",
                },
            ],
            "while": "Do you want to create another file?",
        }
    ]
    data = [
        {
            "type": "list",
            "variable": "files",
            "label": "Files",
            "subtype": [
                {
                    "key": "name",
                    "type": "string",
                    "label": "Name",
                    "question": "What file should this module create?",
                },
                {
                    "key": "content",
                    "type": "string",
                    "label": "Content",
                    "question": "What content should this file have?",
                },
            ],
            "while": "Do you want to create another file?",
            "response": [
                {"name": "/tmp/one.txt", "content": "Hello CFEngine!"},
                {"name": "/tmp/two.txt", "content": "Bye CFEngine!"},
            ],
        }
    ]
    assert input_data_matches_spec(spec, data)

    # A subtype which doesn't match the input definition does not conform:
    data[0]["subtype"][1]["key"] = "bogus"
    assert not input_data_matches_spec(spec, data)


def test_input_data_matches_spec_multiple_variables():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        },
        {
            "type": "string",
            "variable": "content",
            "label": "Content",
            "question": "What content should this file have?",
        },
    ]
    data = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        },
        {
            "type": "string",
            "variable": "content",
            "label": "Content",
            "question": "What content should this file have?",
            "response": "Hello CFEngine!",
        },
    ]
    assert input_data_matches_spec(spec, data)

    data[1]["variable"] = "bogus"
    assert not input_data_matches_spec(spec, data)


def test_input_data_matches_spec_reordered_keys():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        }
    ]
    # The order of the keys doesn't matter:
    data = [
        {
            "variable": "filename",
            "type": "string",
            "label": "Filename",
            "response": "/tmp/create-single-file.txt",
            "question": "What file should this module create?",
        }
    ]
    assert input_data_matches_spec(spec, data)


def test_input_data_matches_spec_changed_value():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        }
    ]
    data = [
        {
            "type": "string",
            "variable": "bogus",
            "label": "Filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    assert not input_data_matches_spec(spec, data)


def test_input_data_matches_spec_renamed_key():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        }
    ]
    data = [
        {
            "doofus": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    assert not input_data_matches_spec(spec, data)


def test_input_data_matches_spec_missing_or_extra_key():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        }
    ]
    missing = [
        {
            "type": "string",
            "variable": "filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    assert not input_data_matches_spec(spec, missing)

    extra = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
            "extra": "not in the input definition",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    assert not input_data_matches_spec(spec, extra)


def test_input_data_matches_spec_not_objects():
    spec = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
        }
    ]
    assert not input_data_matches_spec(spec, ["not an object"])
    assert not input_data_matches_spec(["not an object"], spec)
