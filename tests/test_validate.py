import pytest

from cfbs.utils import CFBSValidationError
from cfbs.validate import validate_module_name_content


def test_validate_module_name_content():
    validate_module_name_content("regular-name")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("Uppercase-name")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("underscore_but_not_local")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("name with spaces")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("-leading-hyphen")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content(
            "module-name-too-longggggggggggggggggggggggggggggggggggggggggggggg"
        )

    validate_module_name_content("./local_module.cf")
    validate_module_name_content("./local_module_directory/")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("not_local_module.cf")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("./_leading_underscore/")
    validate_module_name_content("./good-extension.json")
    with pytest.raises(CFBSValidationError):
        validate_module_name_content("./bad-extension.zip")

    validate_module_name_content("./123 Illeg@l!/legal-name.cf")
