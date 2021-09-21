import json
from collections import OrderedDict

def pretty_file(filename):
    with open(filename) as f:
        data = f.read()
    with open(filename, "w") as f:
        f.write(pretty_string(data))
        f.write("\n")


def pretty_string(s):
    s = json.loads(s, object_pairs_hook=OrderedDict)
    return pretty(s)


def pretty(o):
    MAX_LEN = 80
    INDENT_SIZE = 2

    def _should_wrap(parent):
        assert isinstance(parent, (tuple, list, dict))

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

        if not _should_wrap(lst):
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

        if not _should_wrap(dct):
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
