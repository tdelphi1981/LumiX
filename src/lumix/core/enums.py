"""Core enumerations for LumiX optimization library."""

from enum import Enum


class LXVarType(Enum):
    """Variable types with IDE autocomplete."""

    CONTINUOUS = "continuous"
    INTEGER = "integer"
    BINARY = "binary"


class LXConstraintSense(Enum):
    """Constraint types with IDE autocomplete."""

    LE = "<="
    GE = ">="
    EQ = "=="


class LXObjectiveSense(Enum):
    """Objective directions."""

    MINIMIZE = "min"
    MAXIMIZE = "max"


__all__ = ["LXVarType", "LXConstraintSense", "LXObjectiveSense"]
