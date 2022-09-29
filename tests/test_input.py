import copy
from cfbs.commands import update_input_data, InputDataUpdateFailed

module = {
    "name": "superhero-module",
    "input": [
        {
            "type": "list",
            "variable": "users",
            "label": "Users",
            "subtype": [
                {
                    "key": "username",
                    "type": "string",
                    "label": "Username",
                    "question": "What user do you want to create?",
                    "default": "vader",
                },
                {
                    "key": "group",
                    "type": "string",
                    "label": "Group",
                    "question": "What group should this user be a part of?",
                    "default": "empire",
                },
            ],
            "while": "Do you want to create another user?",
        }
    ],
}
input_data = [
    {
        "type": "list",
        "variable": "users",
        "label": "Users",
        "subtype": [
            {
                "key": "username",
                "type": "string",
                "label": "Username",
                "question": "What user do you want to create?",
                "default": "vader",
            },
            {
                "key": "group",
                "type": "string",
                "label": "Group",
                "question": "What group should this user be a part of?",
                "default": "empire",
            },
        ],
        "while": "Do you want to create another user?",
        "response": [
            {"username": "superman", "group": "superheroes"},
            {"username": "joker", "group": "supervillains"},
        ],
    }
]


def test_update_input_data_change_type():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["type"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = False
    except InputDataUpdateFailed:
        success = True
    assert success

    mod = copy.deepcopy(module)
    mod["input"][0]["subtype"][1]["type"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = False
    except InputDataUpdateFailed:
        success = True
    assert success


def test_update_input_data_change_variable():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["variable"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = False
    except InputDataUpdateFailed:
        success = True
    assert success


def test_update_input_data_change_label():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["label"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = True
    except InputDataUpdateFailed:
        success = False
    assert success

    mod = copy.deepcopy(module)
    mod["input"][0]["subtype"][1]["label"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = True
    except InputDataUpdateFailed:
        success = False
    assert success


def test_update_input_data_change_key():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["subtype"][1]["key"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = False
    except InputDataUpdateFailed:
        success = True
    assert success


def test_update_input_data_change_question():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["subtype"][1]["question"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = True
    except InputDataUpdateFailed:
        success = False
    assert success


def test_update_input_data_change_while():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["while"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = True
    except InputDataUpdateFailed:
        success = False
    assert success


def test_update_input_data_change_number():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"].append(
        {
            "type": "string",
            "variable": "host",
            "label": "Host",
            "question": "What host do you want to make changes on?",
            "response": "mainframe.batcave.gotham",
        }
    )
    try:
        update_input_data(mod, inp)
        success = False
    except InputDataUpdateFailed:
        success = True
    assert success

    mod = copy.deepcopy(module)
    mod["input"][0]["subtype"].append(
        {
            "key": "homedir",
            "type": "string",
            "label": "Home directory",
            "question": "What should the home directory be?",
        }
    )
    try:
        update_input_data(mod, inp)
        success = False
    except InputDataUpdateFailed:
        success = True
    assert success


def test_update_input_data_change_default():
    mod = copy.deepcopy(module)
    inp = copy.deepcopy(input_data)
    mod["input"][0]["subtype"][1]["default"] = "bogus"
    try:
        update_input_data(mod, inp)
        success = True
    except InputDataUpdateFailed:
        success = False
    assert success
