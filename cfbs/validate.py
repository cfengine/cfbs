"""
Functions for performing the core part of 'cfbs validate'

Iterate over the JSON structure from cfbs.json, and check
the contents against validation rules.

Currently, we are not very strict with validation in other
commands, when you run something like 'cfbs build',
many things only produce warnings. This is for backwards
compatibility and we might choose to turn those warnings
into errors in the future.

Be careful about introducing dependencies to other parts
of the codebase, such as build.py - We want validate.py
to be relatively easy to reuse in various places without
accidentally introducing circular dependencies.
Thus, for example, the common parts needed by both build.py
and validate.py, should be in utils.py or validate.py,
not in build.py.

TODOs:
1. Although we don't import anything from cfbs_config.py
   nor cfbs_json.py, we still depend on them by calling
   certain methods on the config object, such as
   config.warn_about_unknown_keys() and config.find_module().
   We should decouple this so that validate.py is more pure
   and can be called and tested with just simple JSON data
   / dicts. This should make it easer to write unit tests,
   use stricter type checking, and maintain all the validation
   code in one place.
"""

import logging as log
import re
from collections import OrderedDict
from typing import List, Tuple

from cfbs.module import is_module_local
from cfbs.utils import (
    is_a_commit_hash,
    strip_left,
    strip_right_any,
    CFBSExitError,
    CFBSValidationError,
)
from cfbs.pretty import TOP_LEVEL_KEYS, MODULE_KEYS

AVAILABLE_BUILD_STEPS = {
    "copy": 2,
    "run": "1+",
    "delete": "1+",
    "json": 2,
    "append": 2,
    "directory": 2,
    "input": 2,
    "policy_files": "1+",
    "bundles": "1+",
    "replace": 4,  # n, a, b, filename
    "replace_version": 3,  # n, string to replace, filename
}

# Constants / regexes / limits for validating build steps:
MAX_REPLACEMENTS = 1000
FILENAME_RE = r"[-_/a-zA-Z0-9\.]+"
MAX_FILENAME_LENGTH = 128
MAX_BUILD_STEP_LENGTH = 256


def validate_index_string(index):
    assert type(index) is str
    if index.strip() == "":
        raise CFBSValidationError(
            'The "index" string must be a URL / path (string), not "%s" (whitespace)'
            % index
        )
    if not index.endswith(".json"):
        raise CFBSValidationError(
            'The "index" string must refer to a JSON file / URL (ending in .json)'
        )
    if not index.startswith(("https://", "./")):
        raise CFBSValidationError(
            'The "index" string must be a URL (starting with https://) or relative path (starting with ./)'
        )
    if index.startswith("https://") and " " in index:
        raise CFBSValidationError('The "index" URL must not contain spaces')


def split_build_step(command) -> Tuple[str, List[str]]:
    terms = command.split(" ")
    operation, args = terms[0], terms[1:]
    return operation, args


def step_has_valid_arg_count(args, expected):
    actual = len(args)

    if type(expected) is int:
        if actual != expected:
            return False

    else:
        # Only other option is a string of 1+, 2+ or similar:
        assert type(expected) is str and expected.endswith("+")
        expected = int(expected[0:-1])
        if actual < expected:
            return False

    return True


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
        if type(index) is str:
            validate_index_string(index)

    if "provides" in config:
        if type(config["provides"]) not in (dict, OrderedDict):
            raise CFBSValidationError(
                'The "provides" field must be an object (dictionary)'
            )


def validate_module_name_content(name):
    MAX_MODULE_NAME_LENGTH = 64

    if len(name) > MAX_MODULE_NAME_LENGTH:
        raise CFBSValidationError(
            name,
            "Module name is too long (over "
            + str(MAX_MODULE_NAME_LENGTH)
            + " characters)",
        )

    # lowercase ASCII alphanumericals, starting with a letter, and possible singular dashes in the middle
    r = "[a-z][a-z0-9]*(-[a-z0-9]+)*"
    proper_name = name

    if is_module_local(name):
        if not name.startswith("./"):
            raise CFBSValidationError(name, "Local module names should begin with `./`")

        if not name.endswith((".cf", ".json", "/")):
            raise CFBSValidationError(
                name,
                "Local module names should end with `/` (for directories) or `.json` or `.cf` (for files).",
            )

        proper_name = strip_left(proper_name, "./")
        proper_name = strip_right_any(proper_name, ("/", ".cf", ".json"))

        # allow underscores, only for local modules
        proper_name = proper_name.replace("_", "-")

    if not re.fullmatch(r, proper_name):
        raise CFBSValidationError(
            name,
            "Module name contains illegal characters (only lowercase ASCII alphanumeric characters are legal)",
        )

    log.debug("Validated name of module %s" % name)


def validate_config_raise_exceptions(config, empty_build_list_ok=False):
    # First validate the config i.e. the user's cfbs.json
    # Here we can raise exceptions, that's what the rest of
    # the function does, and they are caught by validate_config()
    config.warn_about_unknown_keys(raise_exceptions=True)
    _validate_top_level_keys(config)
    raw_data = config.raw_data

    if config["type"] == "policy-set" or "build" in config:
        _validate_config_for_build_field(config, empty_build_list_ok)

    if "index" in raw_data and type(raw_data["index"]) in (dict, OrderedDict):
        for name, module in raw_data["index"].items():
            validate_single_module("index", name, module, config)

    if "provides" in raw_data:
        for name, module in raw_data["provides"].items():
            validate_single_module("provides", name, module, config)

    if config["type"] == "module":
        validate_module_name_content(config["name"])


def validate_config(config, empty_build_list_ok=False):
    """Returns `0` if there are no validation errors, and `1` otherwise."""
    try:
        validate_config_raise_exceptions(config, empty_build_list_ok)
        return 0
    except CFBSValidationError as e:
        print(e)
        return 1


def validate_build_step(name, module, i, operation, args, strict=False):
    assert type(name) is str
    assert type(module) is not str
    assert type(i) is int

    if strict:
        step = operation + " " + " ".join(args)
        if len(step) > MAX_FILENAME_LENGTH:
            raise CFBSValidationError(
                "%s build step in '%s' is too long" % (operation, name)
            )

    if operation not in AVAILABLE_BUILD_STEPS:
        raise CFBSValidationError(
            name,
            'Unknown operation "%s" in "steps", must be one of: %s (build step %s in module "%s")'
            % (operation, ", ".join(AVAILABLE_BUILD_STEPS), i, name),
        )
    expected = AVAILABLE_BUILD_STEPS[operation]
    actual = len(args)
    if not step_has_valid_arg_count(args, expected):
        if type(expected) is int:
            raise CFBSValidationError(
                name,
                "The %s build step expects %d arguments, %d were given (build step "
                % (operation, expected, actual),
            )
        else:
            expected = int(expected[0:-1])
            raise CFBSValidationError(
                name,
                "The %s build step expects %d or more arguments, %d were given"
                % (operation, expected, actual),
            )
    if not strict:
        return
    if operation == "replace":
        assert len(args) == 4
        n, a, b, filename = args
        assert type(a) is str and a != ""
        assert type(b) is str and b != ""
        assert type(filename) is str and filename != ""
        or_more = False
        if n.endswith("+"):
            n = n[0:-1]
            or_more = True
        try:
            n = int(n)
            assert n >= 1
        except:
            raise CFBSValidationError(
                "replace build step cannot replace something '%s' times" % (args[0],)
            )
        if n > MAX_REPLACEMENTS or n == MAX_REPLACEMENTS and or_more:
            raise CFBSValidationError(
                "replace build step cannot replace something more than %s times"
                % (MAX_REPLACEMENTS,)
            )
        if a in b:
            raise CFBSValidationError(
                "'%s' must not contain '%s' in replace build step (could lead to recursive replacing)"
                % (a, b)
            )
        if filename == "." or filename.endswith(("/", "/.")):
            raise CFBSValidationError(
                "replace build step works on files, not '%s'" % (filename,)
            )
        if filename.startswith("/"):
            raise CFBSValidationError(
                "replace build step works on relative file paths, not '%s'"
                % (filename,)
            )
        if filename.startswith("./"):
            raise CFBSValidationError(
                "replace file paths are always relative, drop the ./ in '%s'"
                % (filename,)
            )
        if ".." in filename:
            raise CFBSValidationError(
                ".. not allowed in replace file path ('%s')" % (filename,)
            )
        if "/./" in filename:
            raise CFBSValidationError(
                "/./ not allowed in replace file path ('%s')" % (filename,)
            )
        if not re.fullmatch(FILENAME_RE, filename):
            raise CFBSValidationError(
                "filename in replace build step contains illegal characters ('%s')"
                % (filename,)
            )

    elif operation == "replace_version":
        assert len(args) == 3
        n, to_replace, filename = args

        # These should be guaranteed by the build step splitting logic:
        assert type(n) is str and n != ""
        assert type(to_replace) is str and to_replace != ""
        assert type(filename) is str and filename != ""

        # replace_version requires the module to have a version field:
        if "version" not in module:
            raise CFBSValidationError(
                name,
                "Module '%s' missing \"version\" field for replace_version build step"
                % (name,),
            )
        version = module["version"]
        # Reuse validation logic for replace:
        validate_build_step(
            name, module, i, "replace", [n, to_replace, version, filename], strict
        )
    else:
        # TODO: Add more validation of other build steps.
        pass


def _validate_module_alias(name, module, context, config):
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
        raise CFBSValidationError(name, '"alias" cannot be used with other attributes')
    if type(module["alias"]) is not str:
        raise CFBSValidationError(name, '"alias" must be of type string')
    if not module["alias"]:
        raise CFBSValidationError(name, '"alias" must be non-empty')
    validate_module_name_content(name)
    if not config.can_reach_dependency(module["alias"], search_in):
        raise CFBSValidationError(
            name, '"alias" must reference another module in the index'
        )
    if "alias" in config.find_module(module["alias"], search_in):
        raise CFBSValidationError(name, '"alias" cannot reference another alias')


def _validate_module_name(name: str, module):
    assert "name" in module
    assert name
    assert type(name) is str
    assert module["name"]
    assert type(module["name"]) is str
    assert name == module["name"]
    if type(module["name"]) is not str:
        raise CFBSValidationError(name, '"name" must be of type string')
    if not module["name"]:
        raise CFBSValidationError(name, '"name" must be non-empty')

    validate_module_name_content(name)


def _validate_module_description(name, module):
    assert "description" in module
    if type(module["description"]) is not str:
        raise CFBSValidationError(name, '"description" must be of type string')
    if not module["description"]:
        raise CFBSValidationError(name, '"description" must be non-empty')


def _validate_module_tags(name, module):
    assert "tags" in module
    if type(module["tags"]) is not list:
        raise CFBSValidationError(name, '"tags" must be of type list')
    for tag in module["tags"]:
        if type(tag) is not str:
            raise CFBSValidationError(name, '"tags" must be a list of strings')


def _validate_module_repo(name, module):
    assert "repo" in module
    if type(module["repo"]) is not str:
        raise CFBSValidationError(name, '"repo" must be of type string')
    if not module["repo"]:
        raise CFBSValidationError(name, '"repo" must be non-empty')


def _validate_module_by(name, module):
    assert "by" in module
    if type(module["by"]) is not str:
        raise CFBSValidationError(name, '"by" must be of type string')
    if not module["by"]:
        raise CFBSValidationError(name, '"by" must be non-empty')


def _validate_module_dependencies(name, module, config, context, local_check=False):
    assert name
    assert module
    assert context in ("build", "provides", "index")
    if local_check:
        assert config is None
    else:
        assert config

    if local_check:
        search_in = None
    elif context == "build":
        search_in = ("build",)
    elif context == "provides":
        search_in = ("index", "provides")
    else:
        assert context == "index"
        search_in = ("index",)
    assert "dependencies" in module
    if type(module["dependencies"]) is not list:
        raise CFBSValidationError(
            name, 'Value of attribute "dependencies" must be of type list'
        )
    for dependency in module["dependencies"]:
        if type(dependency) is not str:
            raise CFBSValidationError(name, '"dependencies" must be a list of strings')
        if local_check:
            continue
        assert config
        if not config.can_reach_dependency(dependency, search_in):
            raise CFBSValidationError(
                name,
                '"dependencies" references a module which could not be found: "%s"'
                % dependency,
            )
        if "alias" in config.find_module(dependency):
            raise CFBSValidationError(name, '"dependencies" cannot reference an alias')


def _validate_module_index(name, module):
    assert "index" in module
    if type(module["index"]) is not str:
        raise CFBSValidationError(name, '"index" in "%s" must be a string' % name)
    try:
        validate_index_string(module["index"])
    except CFBSValidationError as e:
        msg = str(e) + " (in module '%s')" % name
        raise CFBSValidationError(msg)


def _validate_module_version(name, module):
    assert "version" in module
    if type(module["version"]) is not str:
        raise CFBSValidationError(name, '"version" must be of type string')
    regex = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-([0-9]+))?"
    if re.fullmatch(regex, module["version"]) is None:
        raise CFBSValidationError(name, '"version" must match regex %s' % regex)


def _validate_module_commit(name, module):
    assert "commit" in module
    commit = module["commit"]
    if type(commit) is not str:
        raise CFBSValidationError(name, '"commit" must be of type string')
    if not is_a_commit_hash(commit):
        raise CFBSValidationError(name, '"commit" must be a commit reference')


def _validate_module_subdirectory(name, module):
    assert "subdirectory" in module
    if type(module["subdirectory"]) is not str:
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


def _validate_module_steps(name, module):
    assert "steps" in module
    if type(module["steps"]) is not list:
        raise CFBSValidationError(name, '"steps" must be of type list')
    if not module["steps"]:
        raise CFBSValidationError(name, '"steps" must be non-empty')
    for i, step in enumerate(module["steps"]):
        if type(step) is not str:
            raise CFBSValidationError(name, '"steps" must be a list of strings')
        if not step or step.strip() == "":
            raise CFBSValidationError(
                name, '"steps" must be a list of non-empty / non-whitespace strings'
            )
        operation, args = split_build_step(step)
        validate_build_step(name, module, i, operation, args)


def _validate_module_url_field(name, module, field):
    assert field in module
    url = module.get(field)
    if url and not url.startswith("https://"):
        raise CFBSValidationError(name, '"%s" must be an HTTPS URL' % field)


def _validate_module_input(name, module):
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
            if "while" not in input_element:
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
            if "subtype" not in input_element:
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


def validate_single_module(context, name, module, config, local_check=False):
    """Function to validate one module object.

    Called repeatedly for each module in index, provides, and build.
    Also called from other places, like in the update command,
    before "accepting" new versions of a module object.
    Planned to be used by cfbs add as well in the future.

    local_check can be set to True if you don't want to check
    references to other parts of the cfbs.json i.e. to disable
    checks for dependencies and aliases. In that case, the function must be
    called with config = None.
    """
    assert context in ("index", "provides", "build")
    if local_check:
        assert config is None
    else:
        assert config

    # Step 1 - Handle special cases (alias):

    if "alias" in module:
        if local_check:
            raise CFBSValidationError(
                "The 'alias' field is not allowed in '%s', inside '$%s'"
                % (name, context)
            )
        # Needs to be validated first because it's missing the other fields:
        _validate_module_alias(name, module, context, config)
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
        _validate_module_name(name, module)
    if "description" in module:
        _validate_module_description(name, module)
    if "tags" in module:
        _validate_module_tags(name, module)
    if "repo" in module:
        _validate_module_repo(name, module)
    if "by" in module:
        _validate_module_by(name, module)
    if "dependencies" in module:
        _validate_module_dependencies(name, module, config, context, local_check)
    if "index" in module:
        _validate_module_index(name, module)
    if "version" in module:
        _validate_module_version(name, module)
    if "commit" in module:
        _validate_module_commit(name, module)
    if "subdirectory" in module:
        _validate_module_subdirectory(name, module)
    if "steps" in module:
        _validate_module_steps(name, module)
    if "website" in module:
        _validate_module_url_field(name, module, "website")
    if "documentation" in module:
        _validate_module_url_field(name, module, "documentation")
    if "input" in module:
        _validate_module_input(name, module)

    # Step 4 - Additional validation checks:

    # Validate module name content also when there's no explicit "name" field (for "index" and "provides" project types)
    if "name" not in module:
        validate_module_name_content(name)


def _validate_config_for_build_field(config, empty_build_list_ok=False):
    """Validate that neccessary fields are in the config for the build/download commands to work"""
    if "build" not in config:
        raise CFBSExitError(
            'A "build" field is missing in ./cfbs.json'
            + " - The 'cfbs build' command loops through all modules in this list to find build steps to perform"
        )
    if type(config["build"]) is not list:
        raise CFBSExitError(
            'The "build" field in ./cfbs.json must be a list (of modules involved in the build)'
        )
    if len(config["build"]) > 0:
        # If there are modules in "build" validate them:
        for index, module in enumerate(config["build"]):
            name = module["name"] if "name" in module else index
            validate_single_module("build", name, module, config)
    elif not empty_build_list_ok:
        raise CFBSExitError(
            "The \"build\" field in ./cfbs.json is empty - add modules with 'cfbs add'"
        )
