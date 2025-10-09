"""Multi-model indexing for LumiX."""

from .cartesian import LXCartesianProduct
from .dimensions import LXIndexDimension

__all__ = ["LXIndexDimension", "LXCartesianProduct"]
