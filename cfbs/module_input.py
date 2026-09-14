"""
Helpers for working with module input definitions and their responses.
"""


def _is_file(definition):
    return isinstance(definition, dict) and definition.get("type") == "file"


def _file_keys(subtype):
    """The keys of a keyed list "subtype" which hold file paths"""
    return [part["key"] for part in subtype if _is_file(part) and "key" in part]


def _transform_keys(entry, keys, transform):
    """Transform the given keys of a single response object"""
    if not isinstance(entry, dict):
        return
    for key in keys:
        if key in entry:
            entry[key] = transform(entry[key])


def map_file_responses(input_data, transform):
    """Apply transform to every file path in a module's input responses.

    Covers a top level "file" input and a "list" input with a "file" subtype.
    Responses are rewritten in place, and anything which isn't a file path is
    left alone.
    """
    if not isinstance(input_data, list):
        return

    for element in input_data:
        if not isinstance(element, dict) or "response" not in element:
            # Without a response there is nothing to map
            continue
        response = element["response"]

        if _is_file(element):
            # Single file
            element["response"] = transform(response)

        elif element.get("type") == "list" and isinstance(response, list):
            subtype = element.get("subtype")

            if _is_file(subtype):
                # List of files
                element["response"] = [transform(path) for path in response]

            elif isinstance(subtype, list):
                # List of objects where one or more keys are files
                keys = _file_keys(subtype)
                for entry in response:
                    _transform_keys(entry, keys, transform)
