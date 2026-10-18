"""Warnings attributed to the user's code, not to LumiX internals."""
import os
import sys
import warnings

_PREFIX = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep  # .../lumix/


def _internal(frame) -> bool:
    # By module name, so the __init__ that @dataclass generates for a LumiX class
    # (file "<string>", module lumix.*) is internal while user code run with
    # ``python -c`` (file "<string>", module __main__) is not.
    module = frame.f_globals.get("__name__", "")
    return module == "lumix" or module.startswith("lumix.") or \
        frame.f_code.co_filename.startswith(_PREFIX)


def warn_user(message: str, category: type = UserWarning) -> None:
    """Warn at the first stack frame outside the lumix package (the user's call)."""
    frame, level = sys._getframe(1), 2
    while frame is not None and _internal(frame):
        frame, level = frame.f_back, level + 1
    warnings.warn(message, category, stacklevel=level)
