from cfbs.module_input import map_file_responses


def _localize(path):
    """Stand-in for what the real callers do to each path they're given"""
    return "$(sys.inputdir)/" + path


def test_map_file_responses_top_level_file():
    """A "file" input asks for one file, so its response is a single path"""
    input_data = [
        {
            "type": "file",
            "variable": "script",
            "label": "Script",
            "question": "Which script should be run?",
            "response": "./run-scripts/deploy.sh",
        }
    ]

    map_file_responses(input_data, _localize)

    assert input_data[0]["response"] == "$(sys.inputdir)/./run-scripts/deploy.sh"


def test_map_file_responses_list_of_files():
    """A "list" whose "subtype" is a lone "file" has a list of paths"""
    input_data = [
        {
            "type": "list",
            "variable": "scripts",
            "label": "Scripts",
            "subtype": {
                "type": "file",
                "label": "Script",
                "question": "Which script should be run?",
            },
            "while": "Do you want to add another script?",
            "response": ["./run-scripts/deploy.sh", "./run-scripts/rollback.sh"],
        }
    ]

    map_file_responses(input_data, _localize)

    assert input_data[0]["response"] == [
        "$(sys.inputdir)/./run-scripts/deploy.sh",
        "$(sys.inputdir)/./run-scripts/rollback.sh",
    ]


def test_map_file_responses_list_of_objects():
    """With a keyed "subtype", each response is an object, and only the keys
    which are files are paths - the rest are values the user typed"""
    input_data = [
        {
            "type": "list",
            "variable": "playbooks",
            "label": "Playbooks",
            "subtype": [
                {
                    "key": "path",
                    "type": "file",
                    "label": "Path",
                    "question": "Which playbook should be run?",
                },
                {
                    "key": "condition",
                    "type": "string",
                    "label": "Condition",
                    "question": "Condition for when to run",
                },
            ],
            "while": "Do you want to specify more playbooks to be run?",
            "response": [
                {"path": "./playbooks/one.yaml", "condition": "linux"},
                {"path": "./playbooks/two.yaml", "condition": "any"},
            ],
        }
    ]

    map_file_responses(input_data, _localize)

    assert input_data[0]["response"] == [
        {"path": "$(sys.inputdir)/./playbooks/one.yaml", "condition": "linux"},
        {"path": "$(sys.inputdir)/./playbooks/two.yaml", "condition": "any"},
    ]


def test_map_file_responses_ignores_strings():
    """Responses to the other input types are values, not paths"""
    input_data = [
        {"type": "string", "variable": "filename", "response": "/tmp/foo.txt"},
        {"type": "string-multiline", "variable": "content", "response": "line\nline"},
        {
            "type": "list",
            "variable": "files",
            "subtype": {"type": "string", "label": "Path", "question": "Path?"},
            "while": "Another?",
            "response": ["/tmp/one.txt", "/tmp/two.txt"],
        },
        {
            "type": "list",
            "variable": "packages",
            "subtype": [
                {"key": "name", "type": "string", "label": "Name", "question": "Name?"},
            ],
            "while": "Another?",
            "response": [{"name": "curl"}],
        },
    ]
    before = [dict(element) for element in input_data]

    map_file_responses(input_data, _localize)

    assert input_data == before


def test_map_file_responses_ignores_malformed_data():
    """During a build the input data is whatever is in the module's input.json,
    which nothing checks against the module's input definition"""
    map_file_responses(None, _localize)
    map_file_responses("not a list", _localize)
    map_file_responses([None, "not an element"], _localize)

    input_data = [
        {
            "type": "list",
            "variable": "playbooks",
            "subtype": [{"key": "path", "type": "file"}],
            "response": ["not an object"],
        }
    ]
    map_file_responses(input_data, _localize)
    assert input_data[0]["response"] == ["not an object"]


def test_map_file_responses_leaves_unanswered_input_alone():
    input_data = [{"type": "file", "variable": "script", "label": "Script"}]

    map_file_responses(input_data, _localize)

    assert input_data == [{"type": "file", "variable": "script", "label": "Script"}]
