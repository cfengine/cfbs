"""
Functions for generating CFEngine augments (def.json)
"""

from collections import OrderedDict

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

    # OrderedDict, so that the keys are in the same order regardless of
    # the Python version. Dictionaries don't preserve the insertion order
    # before Python 3.7:
    augment = OrderedDict()
    augment["variables"] = OrderedDict()

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

        augment_variable = OrderedDict()
        augment_variable["value"] = value
        augment_variable["comment"] = comment
        augment["variables"]["%s:%s.%s" % (namespace, bundle, name)] = augment_variable

    return augment
