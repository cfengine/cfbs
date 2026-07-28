"""
Functions for generating CFEngine augments (def.json)
"""

from cfbs.utils import canonify


def generate_augment(module_name, input_data):
    """
    Generate augment from input data.

    :param module_name: name of module
    :param input_data: input data
    :return: generated augment or None if input data is incomplete
    """
    if not isinstance(input_data, list):
        return None

    augment = {"variables": {}}

    for variable in input_data:
        if not isinstance(variable, dict) or any(
            key not in variable for key in ("variable", "response")
        ):
            continue

        name = variable["variable"]
        namespace = variable.get("namespace", "cfbs")
        bundle = variable.get("bundle", canonify(module_name))
        value = variable["response"]
        comment = variable.get("comment", "Added by 'cfbs input'")

        augment["variables"]["%s:%s.%s" % (namespace, bundle, name)] = {
            "value": value,
            "comment": comment,
        }

    return augment
