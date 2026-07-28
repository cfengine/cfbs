from cfbs.augments import generate_augment


def test_generate_augment_string():
    """The "create single file" example from JSON.md"""
    input_data = [
        {
            "type": "string",
            "variable": "filename",
            "label": "Filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    assert generate_augment("create-single-file", input_data) == {
        "variables": {
            "cfbs:create_single_file.filename": {
                "value": "/tmp/create-single-file.txt",
                "comment": "Added by 'cfbs input'",
            }
        }
    }


def test_generate_augment_multiple_variables():
    """The "create a single file with content" example from JSON.md"""
    input_data = [
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
    assert generate_augment("create-single-file-with-content", input_data) == {
        "variables": {
            "cfbs:create_single_file_with_content.filename": {
                "value": "/tmp/create-single-file.txt",
                "comment": "Added by 'cfbs input'",
            },
            "cfbs:create_single_file_with_content.content": {
                "value": "Hello CFEngine!",
                "comment": "Added by 'cfbs input'",
            },
        }
    }


def test_generate_augment_overridden_defaults():
    """The namespace, bundle, and comment defaults can be overridden"""
    input_data = [
        {
            "type": "string",
            "namespace": "my_namespace",
            "bundle": "my_bundle",
            "variable": "filename",
            "comment": "Example comment.",
            "label": "Filename",
            "question": "What file should this module create?",
            "response": "/tmp/create-single-file.txt",
        }
    ]
    assert generate_augment("create-single-file", input_data) == {
        "variables": {
            "my_namespace:my_bundle.filename": {
                "value": "/tmp/create-single-file.txt",
                "comment": "Example comment.",
            }
        }
    }


def test_generate_augment_list():
    """The "create multiple files" example from JSON.md

    A list with a subtype of a single value, so the responses are
    just strings.
    """
    input_data = [
        {
            "type": "list",
            "variable": "files",
            "label": "Files",
            "subtype": {
                "type": "string",
                "label": "Filename",
                "question": "What file should this module create?",
            },
            "while": "Do you want to create another file?",
            "response": [
                "/tmp/create-multiple-files-1.txt",
                "/tmp/create-multiple-files-2.txt",
            ],
        }
    ]
    assert generate_augment("create-multiple-files", input_data) == {
        "variables": {
            "cfbs:create_multiple_files.files": {
                "value": [
                    "/tmp/create-multiple-files-1.txt",
                    "/tmp/create-multiple-files-2.txt",
                ],
                "comment": "Added by 'cfbs input'",
            }
        }
    }


def test_generate_augment_list_with_keys():
    """The "create multiple files with content" example from JSON.md

    A list with a subtype of multiple values, so the responses are
    objects, keyed by the "key" fields of the subtype.
    """
    input_data = [
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
    assert generate_augment("create-multiple-files-with-content", input_data) == {
        "variables": {
            "cfbs:create_multiple_files_with_content.files": {
                "value": [
                    {"name": "/tmp/one.txt", "content": "Hello CFEngine!"},
                    {"name": "/tmp/two.txt", "content": "Bye CFEngine!"},
                ],
                "comment": "Added by 'cfbs input'",
            }
        }
    }


def test_generate_augment_no_response():
    """Input definitions without a response are skipped"""
    input_data = [
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
            "response": "Hello CFEngine!",
        },
    ]
    assert generate_augment("create-single-file-with-content", input_data) == {
        "variables": {
            "cfbs:create_single_file_with_content.content": {
                "value": "Hello CFEngine!",
                "comment": "Added by 'cfbs input'",
            }
        }
    }

    del input_data[1]["response"]
    assert generate_augment("create-single-file-with-content", input_data) == {
        "variables": {}
    }

    assert generate_augment("create-single-file", []) == {"variables": {}}


def test_generate_augment_not_a_list():
    """Input data which is not a list of input definitions is incomplete"""
    assert generate_augment("create-single-file", None) is None
    assert generate_augment("create-single-file", {"variable": "filename"}) is None
