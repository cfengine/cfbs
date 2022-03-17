from collections import OrderedDict

from cfbs.pretty import pretty


class Module:
    """Class representing a module in cfbs.json"""

    def __init__(
        self,
        arg: str,
    ):
        """Initialize from argument with format `NAME[@VERSION]`"""
        assert isinstance(arg, str)
        if "@" in arg:
            self.name, self.version = arg.split("@")
        else:
            self.name = arg

    def __setattr__(self, name: str, value):
        if name in Module.attributes():
            if name in ("steps", "tags", "dependencies"):
                if not isinstance(value, list) or any(
                    not isinstance(e, str) for e in value
                ):
                    raise ValueError("Attribute '%s' must be a list of str" % name)
            elif not isinstance(value, str):
                raise ValueError("Attribute '%s' must be a str" % name)

            mux = {"repo", "url", "path"}
            if name in mux and any(getattr(self, e) for e in mux.difference(name)):
                raise ValueError("Attributes %s are mutually exclusive" % mux)

        super().__setattr__(name, value)

    def __getattr__(self, name: str):
        try:
            return super().__getattr__(name)
        except AttributeError as e:
            if name in Module.attributes():
                return None
            raise e

    def __str__(self) -> str:
        return pretty(self.to_dict())

    def to_dict(self):
        keys = Module.attributes()
        vals = [getattr(self, attr) for attr in keys]
        return OrderedDict((key, val) for key, val in zip(keys, vals) if val)

    @staticmethod
    def attributes() -> tuple:
        return (
            "name",
            "version",
            "commit",
            "added_by",
            "steps",
            "tags",
            "subdirectory",
            "repo",
            "url",
            "path",
            "description",
            "by",
            "dependencies",
        )
