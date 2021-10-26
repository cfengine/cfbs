import argparse
import json
import sys
import requests
import re

from cfbs.utils import is_a_commit_hash


class CFBSIndexException(Exception):
    def __init__(self, name, message) -> None:
        if name is None:
            super().__init__("Error in index: " + message)
        else:
            super().__init__("Error in index for module '%s': " % name + message)


def validate_index(index):
    def validate_alias(name, modules):
        if len(modules[name]) != 1:
            raise CFBSIndexException(
                name, "'alias' cannot be used with other attributes"
            )
        if type(modules[name]["alias"]) != str:
            raise CFBSIndexException(name, "'alias' must be of type string")
        if not modules[name]["alias"]:
            raise CFBSIndexException(name, "'alias' must be non-empty")
        if not modules[name]["alias"] in modules:
            raise CFBSIndexException(name, "'alias' must reference another module")
        if "alias" in modules[modules[name]["alias"]]:
            raise CFBSIndexException(name, "'alias' cannot reference another alias")

    def validate_description(name, modules):
        if not "description" in modules[name]:
            raise CFBSIndexException(name, "Missing required attribute 'description'")
        if type(modules[name]["description"]) != str:
            raise CFBSIndexException(name, "'description' must be of type string")
        if not modules[name]["description"]:
            raise CFBSIndexException(name, "'description' must be non-empty")

    def validate_tags(name, modules):
        if not "tags" in modules[name]:
            raise CFBSIndexException("Missing required attribute 'tags'")
        if type(modules[name]["tags"]) != list:
            raise CFBSIndexException(name, "'tags' must be of type list")
        for tag in modules[name]["tags"]:
            if type(tag) != str:
                raise CFBSIndexException(name, "'tags' must be a list of strings")

    def validate_repo(name, modules):
        if not "repo" in modules[name]:
            raise CFBSIndexException(name, "Missing required attribute 'repo'")
        if type(modules[name]["repo"]) != str:
            raise CFBSIndexException(name, "'repo' must be of type string")
        if not modules[name]["repo"]:
            raise CFBSIndexException(name, "'repo' must be non-empty")
        response = requests.head(modules[name]["repo"])
        if not response.ok:
            raise CFBSIndexException(
                name,
                "HEAD request of repo responded with status code '%d'"
                % response.status_code,
            )

    def validate_by(name, modules):
        if not "by" in modules[name]:
            raise CFBSIndexException(name, "Missing reqired attribute 'by'")
        if type(modules[name]["by"]) != str:
            raise CFBSIndexException(name, "'by' must be of type string")
        if not modules[name]["by"]:
            raise CFBSIndexException(name, "'by' must be non-empty")

    def validate_dependencies(name, modules):
        if type(modules[name]["dependencies"]) != list:
            raise CFBSIndexException(
                name, "Value of attribute 'dependencies' must be of type list"
            )
        for dependency in modules[name]["dependencies"]:
            if type(dependency) != str:
                raise CFBSIndexException(
                    name, "'dependencies' must be a list of strings"
                )
            if not dependency in modules:
                raise CFBSIndexException(name, "'dependencies' reference other modules")
            if "alias" in modules[dependency]:
                raise CFBSIndexException(
                    name, "'dependencies' cannot reference an alias"
                )

    def validate_version(name, modules):
        if not "version" in modules[name]:
            raise CFBSIndexException(name, "Missing required attribute 'version'")
        if type(modules[name]["version"]) != str:
            raise CFBSIndexException(name, "'version' must be of type string")
        regex = r"(0|[1-9][0-9]*).(0|[1-9][0-9]*).(0|[1-9][0-9]*)"
        if re.fullmatch(regex, modules[name]["version"]) == None:
            raise CFBSIndexException(name, "'version' must match regex %s" % regex)

    def validate_commit(name, modules):
        if not "commit" in modules[name]:
            raise CFBSIndexException(name, "Missing required attribute 'commit'")
        commit = modules[name]["commit"]
        if type(commit) != str:
            raise CFBSIndexException(name, "'commit' must be of type string")
        if not is_a_commit_hash(commit):
            raise CFBSIndexException(name, "'commit' must be a commit reference")

    def validate_subdirectory(name, modules):
        if type(modules[name]["subdirectory"]) != str:
            raise CFBSIndexException(name, "'subdirectory' must be of type string")
        if not modules[name]["subdirectory"]:
            raise CFBSIndexException(name, "'subdirectory' must be non-empty")

    def validate_steps(name, modules):
        if not "steps" in modules[name]:
            raise CFBSIndexException(name, "Missing required attribute 'steps'")
        if type(modules[name]["steps"]) != list:
            raise CFBSIndexException(name, "'steps' must be of type list")
        if not modules[name]["steps"]:
            raise CFBSIndexException(name, "'steps' must be non-empty")
        for step in modules[name]["steps"]:
            if type(step) != str:
                raise CFBSIndexException(name, "'steps' must be a list of strings")
            if not step:
                raise CFBSIndexException(name, "'steps' must be a list of non-empty strings")

    def validate_derived_url(name, modules):
        url = modules[name]["repo"]
        url += "/tree/" + modules[name]["commit"]
        if "subdirectory" in modules[name]:
            url += "/" + modules[name]["subdirectory"]
        response = requests.head(url)
        if not response.ok:
            raise CFBSIndexException(
                name,
                "HEAD request of url '%s' responded with status code '%d'"
                % (url, response.status_code),
            )

    def validate_url_field(name, modules, field):
        url = modules[name].get(field)
        if not url:
            return

        if not url.startswith("https://"):
            raise CFBSIndexException(name, "'%s' must be an HTTPS URL" % field)
        try:
            response = requests.head(url)
        except requests.RequestException as e:
            raise CFBSIndexException(
                name, "HEAD request of %s url '%s' failed: %s" % (field, url, e)) from e
        if not response.ok:
            raise CFBSIndexException(
                name,
                "HEAD request of %s url '%s' responded with status code '%d'"
                % (field, url, response.status_code),
            )

    # Make sure index has a collection named modules
    if not "index" in index:
        raise CFBSIndexException(None, "Missing required attribute 'modules'")
    modules = index["index"]

    # Validate each entry in modules
    for name in modules:
        if "alias" in modules[name]:
            validate_alias(name, modules)
        else:
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
            validate_derived_url(name, modules)
            validate_url_field(name, modules, "website")
            validate_url_field(name, modules, "documentation")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()

    with open(args.file, "r") as f:
        data = f.read()
    index = json.loads(data)

    try:
        validate_index(index)
    except CFBSIndexException as e:
        print(e)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
