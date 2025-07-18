YES_NO_CHOICES = ("yes", "y", "no", "n")


def prompt_user(non_interactive: bool, prompt: str, choices=None, default=None):
    if non_interactive:
        if default is None:
            raise ValueError(
                "Missing default value for prompt '%s' in non-interactive mode" % prompt
            )
        else:
            return default

    prompt_separator = " " if prompt.endswith("?") else ": "
    if choices:
        assert (
            default is None or str(default) in choices
        ), "'%s' not 'None' and '%s' not in '%s'" % (default, default, choices)
        choices_str = "/".join(
            choice.upper() if choice == str(default) else choice for choice in choices
        )
        prompt += " [%s]%s" % (choices_str, prompt_separator)
    elif default is not None:
        prompt += " [%s]%s" % (default, prompt_separator)
    else:
        prompt += prompt_separator

    answer = None
    while answer is None:
        try:
            answer = input(prompt)
        except EOFError:
            answer = ""

        if answer == "":
            answer = default
        elif choices and answer not in choices and answer.lower() not in choices:
            print("Invalid value entered, must be one of: %s" % "/".join(choices))
            answer = None

    return answer


def prompt_user_yesno(non_interactive: bool, prompt: str, default="yes"):
    """Returns `True` if the answer is yes, and `False` otherwise."""

    answer = prompt_user(
        non_interactive,
        prompt,
        choices=YES_NO_CHOICES,
        default=default,
    )

    return answer.lower() in ("yes", "y")
