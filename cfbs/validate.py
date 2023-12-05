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
    def validate_alias(name, module):
        assert "alias" in module
        if len(module) != 1:
            raise CFBSValidationError(
                name, '"alias" cannot be used with other attributes'
            )
        if type(module["alias"]) != str:
            raise CFBSValidationError(name, '"alias" must be of type string')
        if not module["alias"]:
            raise CFBSValidationError(name, '"alias" must be non-empty')
        if not module["alias"] in modules:
            raise CFBSValidationError(name, '"alias" must reference another module')
        if "alias" in modules[module["alias"]]:
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

    def validate_dependencies(name, module, modules):
        assert module == modules[name]
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
            if not dependency in modules:
                raise CFBSValidationError(
                    name, '"dependencies" reference other modules'
                )
            if "alias" in modules[dependency]:
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

    def validate_steps(name, module):
        assert "steps" in module
        if type(module["steps"]) != list:
            raise CFBSValidationError(name, '"steps" must be of type list')
        if not module["steps"]:
            raise CFBSValidationError(name, '"steps" must be non-empty')
        for step in module["steps"]:
            if type(step) != str:
                raise CFBSValidationError(name, '"steps" must be a list of strings')
            if not step:
                raise CFBSValidationError(
                    name, '"steps" must be a list of non-empty strings'
                )

    def validate_url_field(name, module, field):
        assert field in module
        url = module.get(field)
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


    # Step 2 - Check for required fields:

    required_fields = ["steps"]

    if mode == "build":
        required_fields.append("name")
    elif mode == "provides":
        required_fields.append("description")
    else:
        assert mode == "index"
        required_fields.append("description")
        required_fields.append("tags")
        required_fields.append("repo")
        required_fields.append("by")
        required_fields.append("version")
        required_fields.append("commit")

    for required_field in required_field:
        if required_field not in module:
            raise CFBSValidationError(name, '"%s" field is required, but missing')

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
        validate_dependencies(name, module, modules)
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
        name = module["name"]
        _validate_module_object("build", name, module, config.index.data["index"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="./cfbs.json")
    args = parser.parse_args()

    config = CFBSConfig.get_instance(filename=args.file, non_interactive=True)
    validate_config(config)

    sys.exit(0)


if __name__ == "__main__":
    main()
