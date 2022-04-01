from collections import OrderedDict
from cfbs.pretty import pretty, pretty_check_string, pretty_string
from cfbs.utils import item_index


def test_pretty():
    # Test primitives
    assert pretty(None) == "null"
    assert pretty(True) == "true"
    assert pretty(False) == "false"
    assert pretty(123) == "123"
    assert pretty(123.456) == "123.456"
    assert pretty("Hello World!") == '"Hello World!"'

    # Test collections
    assert pretty([]) == "[]"
    assert pretty(()) == "[]"
    assert pretty({}) == "{}"

    test = OrderedDict()
    test["a"] = []
    test["b"] = ()
    expected = '{ "a": [], "b": [] }'
    assert pretty(test) == expected

    test = [None, True, False, 1, 1.2, "Hello!"]
    expected = '[null, true, false, 1, 1.2, "Hello!"]'
    assert pretty(test) == expected

    test = (None, True, False, 1, 1.2, "Hello!")
    expected = '[null, true, false, 1, 1.2, "Hello!"]'
    assert pretty(test) == expected

    test = OrderedDict()
    test["a"] = None
    test["b"] = True
    test["c"] = False
    test["d"] = 1
    test["e"] = 1.2
    test["f"] = "Hello!"
    expected = '{ "a": null, "b": true, "c": false, "d": 1, "e": 1.2, "f": "Hello!" }'
    assert pretty(test) == expected

    # Test that strings are escaped correctly:

    test = ""  # Empty string
    expected = '""'  # is represented as "" in JSON, same as python
    assert pretty(test) == expected

    test = r'""'  # Putting double quotes inside the string
    expected = r'"\"\""'  # means they have to be escaped with backslashes
    assert pretty(test) == expected

    test = "\n"  # A newline character
    expected = r'"\n"'  # is encoded as \n, same as python
    assert pretty(test) == expected

    test = r"\ "  # A backslash character
    expected = r'"\\ "'  # represented by two backslashes in JSON
    assert pretty(test) == expected


def test_pretty_string():
    # Test primitives
    assert pretty_string("null") == "null"
    assert pretty_string("true") == "true"
    assert pretty_string("false") == "false"
    assert pretty_string("123") == "123"
    assert pretty_string("123.456") == "123.456"
    assert pretty_string('"Hello World!"') == '"Hello World!"'

    # Test collections
    assert pretty_string("[]") == "[]"
    assert pretty_string("{}") == "{}"

    test = '[null, true, false, 1, 1.2, "Hello!"]'
    expected = '[null, true, false, 1, 1.2, "Hello!"]'
    assert pretty_string(test) == expected

    test = '{ "a": null, "b": true, "c": false, "d": 1, "e": 1.2, "f": "Hello!" }'
    expected = '{ "a": null, "b": true, "c": false, "d": 1, "e": 1.2, "f": "Hello!" }'
    assert pretty_string(test) == expected

    # Test wrapping on dicts based on length
    test = '{ "This": "line", "is": "less", "than": 80, "characters": "don\'t wrap me..." }'
    expected = '{ "This": "line", "is": "less", "than": 80, "characters": "don\'t wrap me..." }'
    assert pretty_string(test) == expected

    test = '{ "This": "line", "is": "equal", "to": 80, "characters": "dont\'t wrap me...." }'
    expected = '{ "This": "line", "is": "equal", "to": 80, "characters": "dont\'t wrap me...." }'
    assert pretty_string(test) == expected

    test = '{ "This": "line", "is": "greater", "than": 80, "characters": "wrap me ........" }'
    expected = """{
  "This": "line",
  "is": "greater",
  "than": 80,
  "characters": "wrap me ........"
}"""
    assert pretty_string(test) == expected

    # Test wrapping on lists based on length
    test = '["This", "line", "is", "less", "than", 80, "characters", "don\'t wrap me", "."]'
    expected = '["This", "line", "is", "less", "than", 80, "characters", "don\'t wrap me", "."]'
    assert pretty_string(test) == expected

    test = '["This", "line", "is", "less", "than", 80, "characters", "don\'t wrap me", ".."]'
    expected = '["This", "line", "is", "less", "than", 80, "characters", "don\'t wrap me", ".."]'
    assert pretty_string(test) == expected

    test = '["This", "line", "is", "less", "than", 80, "characters", "wrap me", ".........."]'
    expected = """[
  "This",
  "line",
  "is",
  "less",
  "than",
  80,
  "characters",
  "wrap me",
  ".........."
]"""
    assert pretty_string(test) == expected

    # Test wrapping based on siblings
    test = '{ "a": { "b": 1, "c": 2 }, "d": { "e": 3, "f": 4 } }'
    expected = """{
  "a": { "b": 1, "c": 2 },
  "d": { "e": 3, "f": 4 }
}"""
    assert pretty_string(test) == expected

    test = '[["a", "b"], ["c", "d"]]'
    expected = """[
  ["a", "b"],
  ["c", "d"]
]"""
    assert pretty_string(test) == expected

    test = '[{ "a": 1, "b": 2}, { "c": 3, "d": 4 }]'
    expected = """[
  { "a": 1, "b": 2 },
  { "c": 3, "d": 4 }
]"""
    assert pretty_string(test) == expected

    test = '{ "a": [1, 2], "b": [3, 4] }'
    expected = """{
  "a": [1, 2],
  "b": [3, 4]
}"""
    assert pretty_string(test) == expected

    test = '[{ "a": [1, 2], "b": [3, 4] }, { "d": [5, 6], "e": [7, 8] }, null]'
    expected = """[
  {
    "a": [1, 2],
    "b": [3, 4]
  },
  {
    "d": [5, 6],
    "e": [7, 8]
  },
  null
]"""
    assert pretty_string(test) == expected

    # Test wrapping based on siblings and length
    test = '[{ "a": [1, 2], "b": [3, 4] }, { "d": [5, 6], "e": [7, 8, "This is a super duper long string which should cause wrapping due to its length"] }]'
    expected = """[
  {
    "a": [1, 2],
    "b": [3, 4]
  },
  {
    "d": [5, 6],
    "e": [
      7,
      8,
      "This is a super duper long string which should cause wrapping due to its length"
    ]
  }
]"""
    assert pretty_string(test) == expected


def test_pretty_check_string():
    assert pretty_check_string(' "Hello" ') == False
    assert pretty_check_string('"Hello"') == True
    assert (
        pretty_check_string(
            """{
  "name": "lars",
  "age": 27
}"""
        )
        == False
    )
    assert pretty_check_string('{ "name": "lars", "age": 27 }') == True


def test_pretty_sorting():
    test_json = """{
  "description": "The official (default) index of modules for CFEngine Build",
  "type": "index",
  "name": "index",
  "index": {
    "autorun": {
      "description": "Enable autorun functionality",
      "version": "1.0.1",
      "tags": ["supported", "management"],
      "by": "https://github.com/olehermanse",
      "repo": "https://github.com/cfengine/modules",
      "subdirectory": "management/autorun",
      "commit": "c3b7329b240cf7ad062a0a64ee8b607af2cb912a",
      "steps": ["json def.json def.json"]
    },
    "ansible": { "alias": "promise-type-ansible" },
    "cir": { "alias": "client-initiated-reporting" },
    "bash-lib": { "alias": "library-for-promise-types-in-bash" },
    "client-initiated": { "alias": "client-initiated-reporting" },
    "client-initiated-reporting": {
      "description": "Enable client initiated reporting and disable pull collection",
      "repo": "https://github.com/cfengine/modules",
      "tags": ["experimental", "reporting"],
      "by": "https://github.com/cfengine",
      "version": "0.1.1",
      "commit": "c3b7329b240cf7ad062a0a64ee8b607af2cb912a",
      "steps": ["json def.json def.json"],
      "subdirectory": "reporting/client-initiated-reporting"
    }
  }
}"""
    top_level_keys = ("name", "description", "type", "index")
    module_keys = (
        "name",
        "description",
        "tags",
        "repo",
        "by",
        "version",
        "commit",
        "subdirectory",
        "dependencies",
        "steps",
    )
    cfbs_sorting_rules = {
        None: (
            lambda child_item: item_index(top_level_keys, child_item[0]),
            {
                "index": (
                    lambda child_item: child_item[0],
                    {
                        ".*": (
                            lambda child_item: item_index(module_keys, child_item[0]),
                            None,
                        )
                    },
                )
            },
        ),
    }

    expected = """{
  "name": "index",
  "description": "The official (default) index of modules for CFEngine Build",
  "type": "index",
  "index": {
    "ansible": { "alias": "promise-type-ansible" },
    "autorun": {
      "description": "Enable autorun functionality",
      "tags": ["supported", "management"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/olehermanse",
      "version": "1.0.1",
      "commit": "c3b7329b240cf7ad062a0a64ee8b607af2cb912a",
      "subdirectory": "management/autorun",
      "steps": ["json def.json def.json"]
    },
    "bash-lib": { "alias": "library-for-promise-types-in-bash" },
    "cir": { "alias": "client-initiated-reporting" },
    "client-initiated": { "alias": "client-initiated-reporting" },
    "client-initiated-reporting": {
      "description": "Enable client initiated reporting and disable pull collection",
      "tags": ["experimental", "reporting"],
      "repo": "https://github.com/cfengine/modules",
      "by": "https://github.com/cfengine",
      "version": "0.1.1",
      "commit": "c3b7329b240cf7ad062a0a64ee8b607af2cb912a",
      "subdirectory": "reporting/client-initiated-reporting",
      "steps": ["json def.json def.json"]
    }
  }
}"""

    assert pretty_string(test_json, cfbs_sorting_rules) == expected
