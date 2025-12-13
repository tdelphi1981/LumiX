"""Visualization dependency compatibility layer.

This module handles optional visualization dependencies gracefully,
allowing the rest of LumiX to work even when visualization packages
are not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

_PLOTLY_AVAILABLE: bool = False
_PANDAS_AVAILABLE: bool = False

# Plotly imports
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots

    _PLOTLY_AVAILABLE = True
except ImportError:
    go: Any = None
    px: Any = None
    make_subplots: Any = None

# Pandas import
try:
    import pandas as pd

    _PANDAS_AVAILABLE = True
except ImportError:
    pd: Any = None


def require_viz_dependencies() -> None:
    """Raise ImportError if visualization dependencies are not installed.

    Raises:
        ImportError: If plotly is not available.

    Examples::

        from lumix.visualization._compat import require_viz_dependencies

        require_viz_dependencies()  # Raises if plotly not installed
    """
    if not _PLOTLY_AVAILABLE:
        raise ImportError(
            "Visualization features require the 'viz' extra. "
            "Install with: pip install lumix-opt[viz]"
        )


def require_pandas() -> None:
    """Raise ImportError if pandas is not installed.

    Raises:
        ImportError: If pandas is not available.
    """
    if not _PANDAS_AVAILABLE:
        raise ImportError(
            "This feature requires pandas. "
            "Install with: pip install lumix-opt[viz]"
        )


__all__ = [
    "_PLOTLY_AVAILABLE",
    "_PANDAS_AVAILABLE",
    "require_viz_dependencies",
    "require_pandas",
    "go",
    "px",
    "make_subplots",
    "pd",
]