import json
import re
from copy import copy
from collections import OrderedDict

# Globals for the keys in cfbs.json and their order
# Used for validation and prettifying / sorting.
TOP_LEVEL_KEYS = ("name", "description", "type", "index", "git", "provides", "build")

MODULE_KEYS = (
    "alias",
    "name",
    "description",
    "tags",
    "repo",
    "url",
    "by",
    "index",
    "version",
    "commit",
    "subdirectory",
    "dependencies",
    "added_by",
    "steps",
    "input",
)


# These sorting rules achieve 3 things:
# 1. Top level keys are sorted according to a specified list
# 2. Module names in "index" and "provides" are sorted alphabetically
# 3. Fields inside module objects are sorted according to a specified list
#    for "index", "provides", and "build"

_module_key_sorting = (
    MODULE_KEYS,
    None,
)

CFBS_DEFAULT_SORTING_RULES = {
    None: (
        TOP_LEVEL_KEYS,
        {
            "(index|provides)": (
                "alphabetic",  # Module names are sorted alphabetically
                {".*": _module_key_sorting},
            ),
            "build": (  # An array, not an object
                None,  # Don't sort elements of array
                {".*": _module_key_sorting},
            ),
        },
    ),
}


def _children_sort(child: OrderedDict, name, sorting_rules):
    """Recursively sort child objects in a JSON object.

    :param child: child object to start with
    :type child: OrderedDict
    :param name: name of `child` in its parent object (`None` for the top-level object)
    :type name: str or None
    :param sorting_rules: rules for sorting child objects (see below)
    :type sorting_rules: dict

    The `sorting_rules` must be of the following form:

    ```
    {
      "child_name_or_regex": (child_name_key_fn, sorting_rules_inside_child),
      ...
    }
    ```

    where:
    - `child_name_or_regex` is either a string name (key) of a child object,
      or a regular expression matching child object names (keys),
    - `child_name_key_fn` is a key function passed to :func:`sorted` to
      sort the (grand)child objects inside the matching child object(s), and
    - `sorting_rules_inside_child` define the sorting rules inside the matching
      child object(s) using the same structure.

    So the `sorting_rules` dictionary must follow the same structure as the JSON
    object being sorted. For example the following rules:

    ```
    {
        None: (lambda child_item: child_item[0],
               {
                   "modules": (lambda child_item: child_item[0],
                              {
                                  re.compile(r".*"): (lambda child_item: len(child_item[0]), None)
                              })
               })
    }
    ```

    sorts the child objects in the given top-level (`name is not None`) JSON object
    alphabetically by their name, then only inside the `"modules"` object all
    its (grand)child objects are sorted the same way and inside all (`".*"`)
    those (grand)child objects, their (grand-grand)child objects by the lengths
    of their names and then the recursion stops (`None` given as
    `sorting_rules_inside_child`).

    The input JSON is thus supposed to look like this:

    ```
    {
      "something": ...,
      "modules": {
        "mod1": {
          "attr1": ...,
        },
        ...
      },
      "something else",
      ...
    }
    ```

    and the sorting will sort `"something"` `"modules"` and `"something else"`
    alphabetically, then the modules inside `"modules"` alphabetically and then
    the attributes of the modules by their length. No sorting will happen inside
    `"something"` and `"something else"` as well as in the attributes.

    .. note::
       Only JSON objects (dictionaries) are sorted by this function, arrays are ignored.

    """
    assert type(child) is OrderedDict

    for key in child:
        if type(child[key]) not in (list, tuple):
            continue
        if name not in sorting_rules:
            continue
        if key not in sorting_rules[name][1]:
            continue
        rules = sorting_rules[name][1][key][1]
        for element in child[key]:
            if type(element) is OrderedDict:
                _children_sort(element, key, rules)

    rules = None
    if name in sorting_rules.keys():
        rules = sorting_rules[name]
    else:
        for child_key_re in sorting_rules.keys():
            if re.match(child_key_re, name):
                rules = sorting_rules[child_key_re]
                break

    if rules is None:
        return

    child_key_fn = rules[0]

    # This is the same as item_index in utils.py
    # Copy-pasted here to avoid circular import.
    def _item_index(iterable, item, extra_at_end=True):
        try:
            return iterable.index(item)
        except ValueError:
            if extra_at_end:
                return len(iterable)
            else:
                return -1

    # To make this function a bit easier to use / read, allow 2 alternatives to
    # providing key functions:
    # "alphabetic" to sort alphabetically
    # a tuple of strings to sort by this order
    if child_key_fn == "alphabetic":
        child_key_fn = lambda x: x[0]
    if type(child_key_fn) in (tuple, list):
        values = copy(child_key_fn)
        child_key_fn = lambda x: _item_index(values, x[0])

    if child_key_fn is not None:
        for key, value in sorted(child.items(), key=child_key_fn):
            child.move_to_end(key)

    child_sorting_rules = rules[1]
    if child_sorting_rules is not None:
        for child_key, child_value in child.items():
            if type(child_value) is OrderedDict:
                _children_sort(child_value, child_key, child_sorting_rules)


def pretty_check_file(filename, sorting_rules=None):
    with open(filename) as f:
        s = f.read()
    o = json.loads(s, object_pairs_hook=OrderedDict)
    return s == pretty(o, sorting_rules) + "\n"


def pretty_check_string(s, sorting_rules=None):
    o = json.loads(s, object_pairs_hook=OrderedDict)
    return s == pretty(o, sorting_rules)


def pretty_file(filename, sorting_rules=None):
    with open(filename) as f:
        old_data = f.read()
    new_data = pretty_string(old_data, sorting_rules) + "\n"
    if old_data != new_data:
        with open(filename, "w") as f:
            f.write(new_data)
        return True
    return False


def pretty_string(s, sorting_rules=None):
    s = json.loads(s, object_pairs_hook=OrderedDict)
    return pretty(s, sorting_rules)


def pretty(o, sorting_rules=None):
    MAX_LEN = 80
    INDENT_SIZE = 2

    if sorting_rules is not None:
        _children_sort(o, None, sorting_rules)

    def _should_wrap(parent, indent):
        assert isinstance(parent, (tuple, list, dict))
        # We should wrap the top level collection
        if indent == 0:
            return True
        if isinstance(parent, dict):
            parent = parent.values()

        count = 0
        for child in parent:
            if isinstance(child, (tuple, list, dict)):
                if len(child) >= 2:
                    count += 1
        return count >= 2

    def _encode_list(lst, indent, cursor):
        if not lst:
            return "[]"
        if not _should_wrap(lst, indent):
            buf = json.dumps(lst)
            assert "\n" not in buf
            if indent + cursor + len(buf) <= MAX_LEN:
                return buf

        indent += INDENT_SIZE
        buf = "[\n" + " " * indent
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf += ",\n" + " " * indent
            buf += _encode(value, indent, 0)
        indent -= INDENT_SIZE
        buf += "\n" + " " * indent + "]"

        return buf

    def _encode_dict(dct, indent, cursor):
        if not dct:
            return "{}"
        if not _should_wrap(dct, indent):
            buf = json.dumps(dct)
            buf = "{ " + buf[1 : len(buf) - 1] + " }"
            assert "\n" not in buf
            if indent + cursor + len(buf) <= MAX_LEN:
                return buf

        indent += INDENT_SIZE
        buf = "{\n" + " " * indent
        first = True
        for key, value in dct.items():
            if first:
                first = False
            else:
                buf += ",\n" + " " * indent
            if not isinstance(key, str):
                raise ValueError("Illegal key type '" + type(key).__name__ + "'")
            entry = '"' + key + '": '
            buf += entry + _encode(value, indent, len(entry))
        indent -= INDENT_SIZE
        buf += "\n" + " " * indent + "}"

        return buf

    def _encode(data, indent, cursor):
        if data is None:
            return "null"
        elif data is True:
            return "true"
        elif data is False:
            return "false"
        elif isinstance(data, (int, float)):
            return repr(data)
        elif isinstance(data, str):
            # Use the json module to escape the string with backslashes:
            return json.dumps(data)
        elif isinstance(data, (list, tuple)):
            return _encode_list(data, indent, cursor)
        elif isinstance(data, dict):
            return _encode_dict(data, indent, cursor)
        else:
            raise ValueError("Illegal value type '" + type(data).__name__ + "'")

    return _encode(o, 0, 0)
