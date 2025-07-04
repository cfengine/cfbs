from collections import OrderedDict
from cfbs.pretty import pretty, pretty_check_string, pretty_string, pretty_file
from cfbs.utils import item_index, mkdir, read_file


def test_pretty():
    # Test primitives
    assert pretty(None) == "null"
    assert pretty(True) == "true"
    assert pretty(False) == "false"
    assert pretty(123) == "123"
    assert pretty(123.456) == "123.456"
    assert pretty("Hello World!") == '"Hello World!"'

    # Test collections
    assert pretty([]) == ("[]")
    assert pretty(()) == "[]"
    assert pretty({}) == "{}"

    test = OrderedDict()
    test["a"] = []
    test["b"] = ()
    expected = """{
  "a": [],
  "b": []
}"""
    assert pretty(test) == expected

    test = [None, True, False, 1, 1.2, "Hello!"]
    expected = """[
  null,
  true,
  false,
  1,
  1.2,
  "Hello!"
]"""
    assert pretty(test) == expected

    test = (None, True, False, 1, 1.2, "Hello!")
    expected = """[
  null,
  true,
  false,
  1,
  1.2,
  "Hello!"
]"""
    assert pretty(test) == expected

    test = OrderedDict()
    test["a"] = None
    test["b"] = True
    test["c"] = False
    test["d"] = 1
    test["e"] = 1.2
    test["f"] = "Hello!"
    expected = """{
  "a": null,
  "b": true,
  "c": false,
  "d": 1,
  "e": 1.2,
  "f": "Hello!"
}"""
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
    expected = """[
  null,
  true,
  false,
  1,
  1.2,
  "Hello!"
]"""
    assert pretty_string(test) == expected

    test = '{ "a": null, "b": true, "c": false, "d": 1, "e": 1.2, "f": "Hello!" }'
    expected = """{
  "a": null,
  "b": true,
  "c": false,
  "d": 1,
  "e": 1.2,
  "f": "Hello!"
}"""

    assert pretty_string(test) == expected

    test = '{ "This": "line", "is": "equal", "to": 80, "characters": "wrap me anyway" }'
    expected = """{
  "This": "line",
  "is": "equal",
  "to": 80,
  "characters": "wrap me anyway"
}"""
    assert pretty_string(test) == expected

    test = '["This", "line", "is", "more", "than", 80, "characters", "wrap me", ".........."]'
    expected = """[
  "This",
  "line",
  "is",
  "more",
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
    test = (
        '[{ "a": [1, 2], "b": [3, 4] }, { "d": [5, 6], "e": '
        + '[7, 8, "This is a super duper long string which should cause wrapping due to its length"] }]'
    )
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


def test_pretty_file():
    mkdir("tests/tmp/", exist_ok=True)
    with open("tests/tmp/test_pretty_file.json", "w") as f:
        f.write(" {} \n")
    assert pretty_file("tests/tmp/test_pretty_file.json") is True
    assert read_file("tests/tmp/test_pretty_file.json") == "{}\n"
    assert pretty_file("tests/tmp/test_pretty_file.json") is False


def test_pretty_check_string():
    assert pretty_check_string(' "Hello" ') is False
    assert pretty_check_string('"Hello"') is True
    assert (
        pretty_check_string(
            """{
  "name": "lars",
  "age": 27
}"""
        )
        is True
    )
    assert pretty_check_string('{ "name": "lars", "age": 27 }') is False


def test_pretty_sorting_simple_top_level():
    """Show that simple ways of sorting top level keys work"""

    lex_sorting = {
        None: (
            "alphabetic",  # Sort keys lexically / alphabetically
            None,
        ),
    }
    assert pretty_string("""{}""", lex_sorting) == """{}"""
    assert (
        pretty_string("""{"a":1}""", lex_sorting)
        == """{
  "a": 1
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1}""", lex_sorting)
        == """{
  "a": 1,
  "b": 2
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1,"c":3}""", lex_sorting)
        == """{
  "a": 1,
  "b": 2,
  "c": 3
}"""
    )

    length_sorting = {
        None: (
            lambda x: len(x[0]),  # Sort by the length of the key
            None,
        ),
    }

    assert pretty_string("""{}""", length_sorting) == """{}"""
    assert (
        pretty_string("""{"aa":1}""", length_sorting)
        == """{
  "aa": 1
}"""
    )

    assert (
        pretty_string("""{"bbb":2,"aa":1}""", length_sorting)
        == """{
  "aa": 1,
  "bbb": 2
}"""
    )

    assert (
        pretty_string("""{"bbb":2,"aa":1,"c":3}""", length_sorting)
        == """{
  "c": 3,
  "aa": 1,
  "bbb": 2
}"""
    )

    integer_sorting = {
        None: (
            lambda x: x[1],  # Sort by the value (integer)
            None,
        ),
    }

    assert pretty_string("""{}""", integer_sorting) == """{}"""
    assert (
        pretty_string("""{"a":1}""", integer_sorting)
        == """{
  "a": 1
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1}""", integer_sorting)
        == """{
  "a": 1,
  "b": 2
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1,"c":3}""", integer_sorting)
        == """{
  "a": 1,
  "b": 2,
  "c": 3
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1,"c":3,"z":-1}""", integer_sorting)
        == """{
  "z": -1,
  "a": 1,
  "b": 2,
  "c": 3
}"""
    )

    specific_sorting = {
        None: (
            ["z", "b", "a", "c"],
            None,
        ),
    }

    assert pretty_string("""{}""", specific_sorting) == """{}"""

    assert (
        pretty_string("""{"a":1}""", specific_sorting)
        == """{
  "a": 1
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1}""", specific_sorting)
        == """{
  "b": 2,
  "a": 1
}"""
    )

    assert (
        pretty_string("""{"b":2,"a":1,"c":3}""", specific_sorting)
        == """{
  "b": 2,
  "a": 1,
  "c": 3
}"""
    )
    assert (
        pretty_string("""{"b":2,"a":1,"c":3,"z":-1}""", specific_sorting)
        == """{
  "z": -1,
  "b": 2,
  "a": 1,
  "c": 3
}"""
    )


def test_pretty_sorting_array():
    """Test that we can sort the keys inside objects in an array"""
    data = """{
        "yes":[{"a": 1, "b": 2, "c": 3}, {"a": 4, "c": 5, "b": 6}, {"b": 7, "c": 8, "a": 9}],
        "no": [{"a": 1, "b": 2, "c": 3}, {"a": 4, "c": 5, "b": 6}, {"b": 7, "c": 8, "a": 9}]
    }"""

    sorting = {
        None: (
            None,  # Top level keys ("yes", "no") will not be sorted
            {
                "yes": (  # Recurse into "yes" key, ignore "no" key
                    None,  # No sorting for indices of "yes" array
                    {
                        ".*": (  # all keys inside each element will be sorted
                            "alphabetic",
                            None,
                        )
                    },
                )
            },
        ),
    }
    expected = """{
  "yes": [
    { "a": 1, "b": 2, "c": 3 },
    { "a": 4, "b": 6, "c": 5 },
    { "a": 9, "b": 7, "c": 8 }
  ],
  "no": [
    { "a": 1, "b": 2, "c": 3 },
    { "a": 4, "c": 5, "b": 6 },
    { "b": 7, "c": 8, "a": 9 }
  ]
}"""
    assert pretty_string(data, sorting) == expected


def test_pretty_sorting_real_examples():
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
