import argparse
import json
import sys
import re
from collections import OrderedDict

from cfbs.utils import is_valid_arg_count, is_a_commit_hash, split_command, user_error
from cfbs.pretty import TOP_LEVEL_KEYS, MODULE_KEYS
from cfbs.cfbs_config import CFBSConfig
from cfbs.build import AVAILABLE_BUILD_STEPS


class CFBSValidationError(Exception):
    def __init__(self, name_or_message, message=None) -> None:
        assert name_or_message
        if message:
            name = name_or_message
        else:
            name = None
            message = name_or_message
        if name is None:
            super().__init__("Error in cfbs.json: " + message)
        elif type(name) is int:
            super().__init__(
                "Error in cfbs.json for module at index %d: " % name + message
            )
        else:
            super().__init__("Error in cfbs.json for module '%s': " % name + message)


def _validate_top_level_keys(config):
    # Convert the CFBSJson object to a simple dictionary with exactly
    # what was in the file. We don't want CFBSJson / CFBSConfig to do any
    # translations here:
    config = config.raw_data

    # Check that required fields are there:

    required_fields = ["name", "type", "description"]

    for field in required_fields:
        assert field in TOP_LEVEL_KEYS
        if field not in config:
            raise CFBSValidationError(
                'The "%s" field is required in a cfbs.json file' % field
            )

    # Specific error checking for "index" type files:

    if config["type"] == "index" and "index" not in config:
        raise CFBSValidationError(
            'For a cfbs.json with "index" as type, put modules in the index by adding them to a "index" field'
        )
    if config["type"] == "index" and type(config["index"]) not in (dict, OrderedDict):
        raise CFBSValidationError(
            'For a cfbs.json with "index" as type, the "index" field must be an object / dictionary'
            % field
        )

    # Further check types / values of those required fields:

    if type(config["name"]) is not str or config["name"] == "":
        raise CFBSValidationError('The "name" field must be a non-empty string')
    if config["type"] not in ("policy-set", "index", "module"):
        raise CFBSValidationError(
            'The "type" field must be "policy-set", "index", or "module"'
        )
    if type(config["description"]) is not str:
        raise CFBSValidationError('The "description" field must be a string')

    # Check types / values of other optional fields:

    if "git" in config and config["git"] not in (True, False):
        raise CFBSValidationError('The "git" field must be true or false')

    if "index" in config:
        index = config["index"]
        if type(index) not in (str, dict, OrderedDict):
            raise CFBSValidationError(
                'The "index" field must either be a URL / path (string) or an inline index (object / dictionary)'
            )
        if type(index) is str and index.strip() == "":
            raise CFBSValidationError(
                'The "index" string must be a URL / path (string), not "%s"' % index
            )
        if type(index) is str and not index.endswith(".json"):
            raise CFBSValidationError(
                'The "index" string must refer to a JSON file / URL (ending in .json)'
            )
        if type(index) is str and not index.startswith(("https://", "./")):
            raise CFBSValidationError(
                'The "index" string must be a URL (starting with https://) or relative path (starting with ./)'
            )
        if type(index) is str and index.startswith("https://") and " " in index:
            raise CFBSValidationError('The "index" URL must not contain spaces')

    if "provides" in config:
        if type(config["provides"]) not in (dict, OrderedDict):
            raise CFBSValidationError(
                'The "provides" field must be an object (dictionary)'
            )


def _validate_config(config, empty_build_list_ok=False):
    # First validate the config i.e. the user's cfbs.json
    config.warn_about_unknown_keys()
    _validate_top_level_keys(config)
    raw_data = config.raw_data

    if config["type"] == "policy-set" or "build" in config:
        _validate_config_for_build_field(config, empty_build_list_ok)

    if "index" in raw_data and type(raw_data["index"]) in (dict, OrderedDict):
        for name, module in raw_data["index"].items():
            _validate_module_object("index", name, module, config)

    if "provides" in raw_data:
        for name, module in raw_data["provides"].items():
            _validate_module_object("provides", name, module, config)


def validate_config(config, empty_build_list_ok=False):
    try:
        _validate_config(config, empty_build_list_ok)
        return 0
    except CFBSValidationError as e:
        print(e)
        return 1


def _validate_module_object(context, name, module, config):
    def validate_alias(name, module, context):
        if context == "index":
            search_in = ("index",)
        elif context == "provides":
            search_in = "provides"
        else:
            raise CFBSValidationError(
                name, '"alias" is only allowed inside "index" or "provides"'
            )
        assert "alias" in module
        if len(module) != 1:
            raise CFBSValidationError(
                name, '"alias" cannot be used with other attributes'
            )
        if type(module["alias"]) != str:
            raise CFBSValidationError(name, '"alias" must be of type string')
        if not module["alias"]:
            raise CFBSValidationError(name, '"alias" must be non-empty')
        if not config.can_reach_dependency(module["alias"], search_in):
            raise CFBSValidationError(
                name, '"alias" must reference another module in the index'
            )
        if "alias" in config.find_module(module["alias"], search_in):
            raise CFBSValidationError(name, '"alias" cannot reference another alias')

    def validate_name(name, module):
        assert "name" in module
        assert name == module["name"]
        if type(module["name"]) != str:
            raise CFBSValidationError(name, '"name" must be of type string')
        if not module["name"]:
            raise CFBSValidationError(name, '"name" must be non-empty')

    def validate_description(name, module):
        assert "description" in module
        if type(module["description"]) != str:
            raise CFBSValidationError(name, '"description" must be of type string')
        if not module["description"]:
            raise CFBSValidationError(name, '"description" must be non-empty')

    def validate_tags(name, module):
        assert "tags" in module
        if type(module["tags"]) != list:
            raise CFBSValidationError(name, '"tags" must be of type list')
        for tag in module["tags"]:
            if type(tag) != str:
                raise CFBSValidationError(name, '"tags" must be a list of strings')

    def validate_repo(name, module):
        assert "repo" in module
        if type(module["repo"]) != str:
            raise CFBSValidationError(name, '"repo" must be of type string')
        if not module["repo"]:
            raise CFBSValidationError(name, '"repo" must be non-empty')

    def validate_by(name, module):
        assert "by" in module
        if type(module["by"]) != str:
            raise CFBSValidationError(name, '"by" must be of type string')
        if not module["by"]:
            raise CFBSValidationError(name, '"by" must be non-empty')

    def validate_dependencies(name, module, config, context):
        if context == "build":
            search_in = ("build",)
        elif context == "provides":
            search_in = ("index", "provides")
        else:
            assert context == "index"
            search_in = ("index",)
        assert "dependencies" in module
        if type(module["dependencies"]) != list:
            raise CFBSValidationError(
                name, 'Value of attribute "dependencies" must be of type list'
            )
        for dependency in module["dependencies"]:
            if type(dependency) != str:
                raise CFBSValidationError(
                    name, '"dependencies" must be a list of strings'
                )
            if not config.can_reach_dependency(dependency, search_in):
                raise CFBSValidationError(
                    name,
                    '"dependencies" references a module which could not be found: "%s"'
                    % dependency,
                )
            if "alias" in config.find_module(dependency):
                raise CFBSValidationError(
                    name, '"dependencies" cannot reference an alias'
                )

    def validate_version(name, module):
        assert "version" in module
        if type(module["version"]) != str:
            raise CFBSValidationError(name, '"version" must be of type string')
        regex = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-([0-9]+))?"
        if re.fullmatch(regex, module["version"]) == None:
            raise CFBSValidationError(name, '"version" must match regex %s' % regex)

    def validate_commit(name, module):
        assert "commit" in module
        commit = module["commit"]
        if type(commit) != str:
            raise CFBSValidationError(name, '"commit" must be of type string')
        if not is_a_commit_hash(commit):
            raise CFBSValidationError(name, '"commit" must be a commit reference')

    def validate_subdirectory(name, module):
        assert "subdirectory" in module
        if type(module["subdirectory"]) != str:
            raise CFBSValidationError(name, '"subdirectory" must be of type string')
        if not module["subdirectory"]:
            raise CFBSValidationError(name, '"subdirectory" must be non-empty')
        if module["subdirectory"].startswith("./"):
            raise CFBSValidationError(name, '"subdirectory" must not start with ./')
        if module["subdirectory"].startswith("/"):
            raise CFBSValidationError(
                name, '"subdirectory" must be a relative path, not starting with /'
            )
        if " " in module["subdirectory"]:
            raise CFBSValidationError(name, '"subdirectory" cannot contain spaces')
        if module["subdirectory"].endswith(("/", "/.")):
            raise CFBSValidationError(name, '"subdirectory" must not end with / or /.')

    def validate_steps(name, module):
        assert "steps" in module
        if type(module["steps"]) != list:
            raise CFBSValidationError(name, '"steps" must be of type list')
        if not module["steps"]:
            raise CFBSValidationError(name, '"steps" must be non-empty')
        for step in module["steps"]:
            if type(step) != str:
                raise CFBSValidationError(name, '"steps" must be a list of strings')
            if not step or step.strip() == "":
                raise CFBSValidationError(
                    name, '"steps" must be a list of non-empty / non-whitespace strings'
                )
            operation, args = split_command(step)
            if not operation in AVAILABLE_BUILD_STEPS:
                x = ", ".join(AVAILABLE_BUILD_STEPS)
                raise CFBSValidationError(
                    name,
                    'Unknown operation "%s" in "steps", must be one of: (%s)'
                    % (operation, x),
                )
            expected = AVAILABLE_BUILD_STEPS[operation]
            actual = len(args)
            if not is_valid_arg_count(args, expected):
                if type(expected) is int:
                    raise CFBSValidationError(
                        name,
                        "The %s build step expects %d arguments, %d were given"
                        % (operation, expected, actual),
                    )
                else:
                    expected = int(expected[0:-1])
                    raise CFBSValidationError(
                        name,
                        "The %s build step expects %d or more arguments, %d were given"
                        % (operation, expected, actual),
                    )

    def validate_url_field(name, module, field):
        assert field in module
        url = module.get(field)
        if url and not url.startswith("https://"):
            raise CFBSValidationError(name, '"%" must be an HTTPS URL' % field)

    def validate_module_input(name, module):
        assert "input" in module
        if type(module["input"]) is not list or not module["input"]:
            raise CFBSValidationError(
                name, 'The module\'s "input" must be a non-empty array'
            )

        required_string_fields = ["type", "variable", "namespace", "bundle", "label"]

        required_string_fields_subtype = ["type", "label", "question"]

        for input_element in module["input"]:
            if type(input_element) not in (dict, OrderedDict) or not input_element:
                raise CFBSValidationError(
                    name,
                    'The module\'s "input" array must consist of non-empty objects (dictionaries)',
                )
            for field in required_string_fields:
                if field not in input_element:
                    raise CFBSValidationError(
                        name,
                        'The "%s" field is required in module input elements' % field,
                    )
                if (
                    type(input_element[field]) is not str
                    or input_element[field].strip() == ""
                ):
                    raise CFBSValidationError(
                        name,
                        'The "%s" field in input elements must be a non-empty / non-whitespace string'
                        % field,
                    )

            if input_element["type"] not in ("string", "list"):
                raise CFBSValidationError(
                    name,
                    'The input "type" must be "string" or "list", not "%s"'
                    % input_element["type"],
                )
            if not re.fullmatch(r"[a-z_]+", input_element["variable"]):
                raise CFBSValidationError(
                    name,
                    '"%s" is not an acceptable variable name, must match regex "[a-z_]+"'
                    % input_element["variable"],
                )
            if not re.fullmatch(r"[a-z_][a-z0-9_]+", input_element["namespace"]):
                raise CFBSValidationError(
                    name,
                    '"%s" is not an acceptable namespace, must match regex "[a-z_][a-z0-9_]+"'
                    % input_element["namespace"],
                )
            if not re.fullmatch(r"[a-z_]+", input_element["bundle"]):
                raise CFBSValidationError(
                    name,
                    '"%s" is not an acceptable bundle name, must match regex "[a-z_]+"'
                    % input_element["bundle"],
                )

            if input_element["type"] == "list":
                if not "while" in input_element:
                    raise CFBSValidationError(
                        name, 'For a "list" input element, a "while" prompt is required'
                    )
                if (
                    type(input_element["while"]) is not str
                    or not input_element["while"].strip()
                ):
                    raise CFBSValidationError(
                        name,
                        'The "while" prompt in an input "list" element must be a non-empty / non-whitespace string',
                    )
                if not "subtype" in input_element:
                    raise CFBSValidationError(
                        name, 'For a "list" input element, a "subtype" is required'
                    )
                if type(input_element["subtype"]) not in (list, dict, OrderedDict):
                    raise CFBSValidationError(
                        name,
                        'The list element "subtype" must be an object or an array of objects (dictionaries)',
                    )
                subtype = input_element["subtype"]
                if type(subtype) is not list:
                    subtype = [subtype]
                for part in subtype:
                    for field in required_string_fields_subtype:
                        if field not in part:
                            raise CFBSValidationError(
                                name,
                                'The "%s" field is required in module input "subtype" objects'
                                % field,
                            )
                        if type(part[field]) is not str or part[field].strip() == "":
                            raise CFBSValidationError(
                                name,
                                'The "%s" field in module input "subtype" objects must be a non-empty / non-whitespace string'
                                % field,
                            )
                    if len(subtype) > 1:
                        # The "key" field is used to create the JSON objects for each
                        # input in a list of "things" which are not just strings,
                        # i.e. consist of multiple values
                        if (
                            "key" not in part
                            or type(part["key"]) is not str
                            or part["key"].strip() == ""
                        ):
                            raise CFBSValidationError(
                                name,
                                'When using module input with type list, and subtype includes multiple values, "key" is required to distinguish them',
                            )
                    if part["type"] != "string":
                        raise CFBSValidationError(
                            name,
                            'Only "string" supported for the "type" of module input list elements, not "%s"'
                            % part["type"],
                        )

    assert context in ("index", "provides", "build")

    # Step 1 - Handle special cases (alias):

    if "alias" in module:
        # Needs to be validated first because it's missing the other fields:
        validate_alias(name, module, context)
        return  # alias entries would fail the other validation below

    # Step 2 - Check for required fields:

    required_fields = ["steps"]

    if context == "build":
        required_fields.append("name")
    elif context == "provides":
        required_fields.append("description")
    else:
        assert context == "index"
        required_fields.extend(
            [
                "description",
                "tags",
                "repo",
                "by",
                "version",
                "commit",
            ]
        )

    for required_field in required_fields:
        assert required_field in MODULE_KEYS
        if required_field not in module:
            raise CFBSValidationError(
                name, '"%s" field is required, but missing' % required_field
            )

    # Step 3 - Validate fields:

    if "name" in module:
        validate_name(name, module)
    if "description" in module:
        validate_description(name, module)
    if "tags" in module:
        validate_tags(name, module)
    if "repo" in module:
        validate_repo(name, module)
    if "by" in module:
        validate_by(name, module)
    if "dependencies" in module:
        validate_dependencies(name, module, config, context)
    if "version" in module:
        validate_version(name, module)
    if "commit" in module:
        validate_commit(name, module)
    if "subdirectory" in module:
        validate_subdirectory(name, module)
    if "steps" in module:
        validate_steps(name, module)
    if "website" in module:
        validate_url_field(name, module, "website")
    if "documentation" in module:
        validate_url_field(name, module, "documentation")
    if "input" in module:
        validate_module_input(name, module)


def _validate_config_for_build_field(config, empty_build_list_ok=False):
    """Validate that neccessary fields are in the config for the build/download commands to work"""
    if not "build" in config:
        user_error(
            'A "build" field is missing in ./cfbs.json'
            + " - The 'cfbs build' command loops through all modules in this list to find build steps to perform"
        )
    if type(config["build"]) is not list:
        user_error(
            'The "build" field in ./cfbs.json must be a list (of modules involved in the build)'
        )
    if len(config["build"]) > 0:
        # If there are modules in "build" validate them:
        for index, module in enumerate(config["build"]):
            name = module["name"] if "name" in module else index
            _validate_module_object("build", name, module, config)
    elif not empty_build_list_ok:
        user_error(
            "The \"build\" field in ./cfbs.json is empty - add modules with 'cfbs add'"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="./cfbs.json")
    args = parser.parse_args()

    config = CFBSConfig.get_instance(filename=args.file, non_interactive=True)
    r = validate_config(config)

    sys.exit(r)


if __name__ == "__main__":
    main()
