"""Warnings attributed to the user's code, not to LumiX internals."""
import os
import sys
import warnings

_PREFIX = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep  # .../lumix/


def _internal(frame) -> bool:
    name = frame.f_code.co_filename
    # "<string>": the __init__ that @dataclass generates for LumiX classes
    return name.startswith(_PREFIX) or name == "<string>"


def warn_user(message: str, category: type = UserWarning) -> None:
    """Warn at the first stack frame outside the lumix package (the user's call)."""
    frame, level = sys._getframe(1), 2
    while frame is not None and _internal(frame):
        frame, level = frame.f_back, level + 1
    warnings.warn(message, category, stacklevel=level)
