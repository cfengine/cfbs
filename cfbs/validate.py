import argparse
import json
import sys
import re

from cfbs.utils import is_a_commit_hash, user_error
from cfbs.cfbs_config import CFBSConfig


class CFBSValidationError(Exception):
    def __init__(self, name, message) -> None:
        if name is None:
            super().__init__("Error in index: " + message)
        else:
            super().__init__("Error in index for module '%s': " % name + message)


def validate_config(config, build=False):
    # First validate the config i.e. the user's cfbs.json

    # TODO: Add more validation for other things in config:
    #       missing keys, types of keys, accepted values, etc.
    #       https://northerntech.atlassian.net/browse/CFE-4060

    if build:
        _validate_config_for_build_field(config)
    else:
        # If we're not expecting to build anything yet
        # (running a build or download command),
        # we will accept a missing build field or empty list.
        # Other bad values should still error:
        if "build" in config and config["build"] != []:
            _validate_config_for_build_field(config)

    # Then resolve the index, and validate that:
    index = config.index
    if not index:
        user_error("Index not found")

    data = index.data
    if "type" not in data:
        user_error("Index is missing a type field")

    if data["type"] != "index":
        user_error("The loaded index has incorrect type: " + str(data["type"]))

    try:
        _validate_index(data)
    except CFBSValidationError as e:
        print(e)
        return 1
    return 0


def _validate_module_object(mode, name, module, modules):
    def validate_alias(name, modules):
        if len(modules[name]) != 1:
            raise CFBSValidationError(
                name, '"alias" cannot be used with other attributes'
            )
        if type(modules[name]["alias"]) != str:
            raise CFBSValidationError(name, '"alias" must be of type string')
        if not modules[name]["alias"]:
            raise CFBSValidationError(name, '"alias" must be non-empty')
        if not modules[name]["alias"] in modules:
            raise CFBSValidationError(name, '"alias" must reference another module')
        if "alias" in modules[modules[name]["alias"]]:
            raise CFBSValidationError(name, '"alias" cannot reference another alias')

    def validate_description(name, modules):
        if not "description" in modules[name]:
            raise CFBSValidationError(name, 'Missing required attribute "description"')
        if type(modules[name]["description"]) != str:
            raise CFBSValidationError(name, '"description" must be of type string')
        if not modules[name]["description"]:
            raise CFBSValidationError(name, '"description" must be non-empty')

    def validate_tags(name, modules):
        if not "tags" in modules[name]:
            raise CFBSValidationError(name, 'Missing required attribute "tags"')
        if type(modules[name]["tags"]) != list:
            raise CFBSValidationError(name, '"tags" must be of type list')
        for tag in modules[name]["tags"]:
            if type(tag) != str:
                raise CFBSValidationError(name, '"tags" must be a list of strings')

    def validate_repo(name, modules):
        if not "repo" in modules[name]:
            raise CFBSValidationError(name, 'Missing required attribute "repo"')
        if type(modules[name]["repo"]) != str:
            raise CFBSValidationError(name, '"repo" must be of type string')
        if not modules[name]["repo"]:
            raise CFBSValidationError(name, '"repo" must be non-empty')

    def validate_by(name, modules):
        if not "by" in modules[name]:
            raise CFBSValidationError(name, 'Missing reqired attribute "by"')
        if type(modules[name]["by"]) != str:
            raise CFBSValidationError(name, '"by" must be of type string')
        if not modules[name]["by"]:
            raise CFBSValidationError(name, '"by" must be non-empty')

    def validate_dependencies(name, modules):
        if type(modules[name]["dependencies"]) != list:
            raise CFBSValidationError(
                name, 'Value of attribute "dependencies" must be of type list'
            )
        for dependency in modules[name]["dependencies"]:
            if type(dependency) != str:
                raise CFBSValidationError(
                    name, '"dependencies" must be a list of strings'
                )
            if not dependency in modules:
                raise CFBSValidationError(
                    name, '"dependencies" reference other modules'
                )
            if "alias" in modules[dependency]:
                raise CFBSValidationError(
                    name, '"dependencies" cannot reference an alias'
                )

    def validate_version(name, modules):
        if not "version" in modules[name]:
            raise CFBSValidationError(name, 'Missing required attribute "version"')
        if type(modules[name]["version"]) != str:
            raise CFBSValidationError(name, '"version" must be of type string')
        regex = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-([0-9]+))?"
        if re.fullmatch(regex, modules[name]["version"]) == None:
            raise CFBSValidationError(name, '"version" must match regex %s' % regex)

    def validate_commit(name, modules):
        if not "commit" in modules[name]:
            raise CFBSValidationError(name, 'Missing required attribute "commit"')
        commit = modules[name]["commit"]
        if type(commit) != str:
            raise CFBSValidationError(name, '"commit" must be of type string')
        if not is_a_commit_hash(commit):
            raise CFBSValidationError(name, '"commit" must be a commit reference')

    def validate_subdirectory(name, modules):
        if type(modules[name]["subdirectory"]) != str:
            raise CFBSValidationError(name, '"subdirectory" must be of type string')
        if not modules[name]["subdirectory"]:
            raise CFBSValidationError(name, '"subdirectory" must be non-empty')

    def validate_steps(name, modules):
        if not "steps" in modules[name]:
            raise CFBSValidationError(name, 'Missing required attribute "steps"')
        if type(modules[name]["steps"]) != list:
            raise CFBSValidationError(name, '"steps" must be of type list')
        if not modules[name]["steps"]:
            raise CFBSValidationError(name, '"steps" must be non-empty')
        for step in modules[name]["steps"]:
            if type(step) != str:
                raise CFBSValidationError(name, '"steps" must be a list of strings')
            if not step:
                raise CFBSValidationError(
                    name, '"steps" must be a list of non-empty strings'
                )

    def validate_url_field(name, modules, field):
        url = modules[name].get(field)
        if url and not url.startswith("https://"):
            raise CFBSValidationError(name, '"%" must be an HTTPS URL' % field)

    assert module == modules[name]
    assert mode in ("index", "provides", "build")

    # Step 1 - Handle special cases (alias):
    if "alias" in modules[name]:
        if mode in ("index", "provides"):
            validate_alias(name, modules)
            return
        else:
            assert mode == "build"
            raise ValidationError(name, '"alias" is not supported in "build"')

    # Step 2 - Validate fields:
    validate_description(name, modules)
    validate_tags(name, modules)
    validate_repo(name, modules)
    validate_by(name, modules)
    if "dependencies" in modules[name]:  # optional attribute
        validate_dependencies(name, modules)
    validate_version(name, modules)
    validate_commit(name, modules)
    if "subdirectory" in modules[name]:  # optional attribute
        validate_subdirectory(name, modules)
    validate_steps(name, modules)
    validate_url_field(name, modules, "website")
    validate_url_field(name, modules, "documentation")


def _validate_index(index):
    # Make sure index has a collection named modules
    if not "index" in index:
        raise CFBSValidationError(None, "Missing required attribute 'index'")
    modules = index["index"]

    # Validate each entry in modules
    for name in modules:
        module = modules[name]
        _validate_module_object("index", name, module, modules)


def _validate_config_for_build_field(config):
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
    if config["build"] == []:
        user_error(
            "The \"build\" field in ./cfbs.json is empty - add modules with 'cfbs add'"
        )
    for index, module in enumerate(config["build"]):
        if not "name" in module:
            user_error(
                "The module at index "
                + str(index)
                + ' of "build" in ./cfbs.json is missing a "name"'
            )
        name = module["name"]
        if type(name) is not str:
            user_error(
                "The module at index "
                + str(index)
                + ' of "build" in ./cfbs.json has a name which is not a string'
            )
        if not name:
            user_error(
                "The module at index "
                + str(index)
                + ' of "build" in ./cfbs.json has an empty name'
            )
        if (
            not "steps" in module
            or type(module["steps"]) is not list
            or module["steps"] == []
        ):
            user_error(
                'Build steps are missing for the "'
                + name
                + '" module in ./cfbs.json - the "steps" field must have a non-empty list of steps to perform (strings)'
            )

        steps = module["steps"]
        not_strings = len([step for step in steps if type(step) is not str])
        if not_strings == 1:
            user_error(
                "The module '"
                + name
                + '\' in "build" in ./cfbs.json has 1 step which is not a string'
            )
        if not_strings > 1:
            user_error(
                "The module '"
                + name
                + '\' in "build" in ./cfbs.json has '
                + str(not_strings)
                + " steps which are not strings"
            )
        empty_strings = len([step for step in steps if step == ""])
        if empty_strings == 1:
            user_error(
                "The module '"
                + name
                + '\' in "build" in ./cfbs.json has 1 step which is empty'
            )
        if empty_strings > 1:
            user_error(
                "The module '"
                + name
                + '\' in "build" in ./cfbs.json has '
                + str(empty_strings)
                + " steps which are empty"
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="./cfbs.json")
    args = parser.parse_args()

    config = CFBSConfig.get_instance(filename=args.file, non_interactive=True)
    validate_config(config)

    sys.exit(0)


if __name__ == "__main__":
    main()
