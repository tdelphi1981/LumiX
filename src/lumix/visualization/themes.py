"""Color schemes and styling for LumiX visualizations.

This module provides consistent color palettes and styling options
for all visualization components.
"""

from __future__ import annotations

from typing import Dict, List

# Primary LumiX color palette
LUMIX_COLORS: List[str] = [
    "#2E86AB",  # Primary blue
    "#A23B72",  # Magenta
    "#F18F01",  # Orange
    "#C73E1D",  # Red
    "#3A7D44",  # Green
    "#6B5B95",  # Purple
    "#88B04B",  # Light green
    "#F7CAC9",  # Pink
]

# Semantic colors for specific purposes
SEMANTIC_COLORS: Dict[str, str] = {
    "success": "#3A7D44",  # Green - for satisfied/optimal
    "warning": "#F18F01",  # Orange - for partial/suboptimal
    "error": "#C73E1D",  # Red - for failed/infeasible
    "info": "#2E86AB",  # Blue - for neutral information
    "binding": "#C73E1D",  # Red - for binding constraints
    "non_binding": "#3A7D44",  # Green - for non-binding constraints
    "positive": "#3A7D44",  # Green - for positive values
    "negative": "#C73E1D",  # Red - for negative values
}

# Plotly templates
TEMPLATES: Dict[str, str] = {
    "light": "plotly_white",
    "dark": "plotly_dark",
    "default": "plotly_white",
    "lumix": "plotly_white",  # Custom template could be defined here
}


def get_color_sequence(theme: str = "lumix") -> List[str]:
    """Get color sequence for a given theme.

    Args:
        theme: Theme name ('lumix', 'plotly', etc.)

    Returns:
        List of hex color strings.

    Examples::

        colors = get_color_sequence("lumix")
        # Returns: ['#2E86AB', '#A23B72', ...]
    """
    if theme == "lumix":
        return LUMIX_COLORS.copy()
    elif theme == "pastel":
        return [
            "#A8D8EA",
            "#AA96DA",
            "#FCBAD3",
            "#FFFFD2",
            "#B5EAD7",
            "#C7CEEA",
            "#FFB7B2",
            "#FFDAC1",
        ]
    elif theme == "bold":
        return [
            "#E63946",
            "#1D3557",
            "#457B9D",
            "#A8DADC",
            "#F4A261",
            "#2A9D8F",
            "#E9C46A",
            "#264653",
        ]
    else:
        return LUMIX_COLORS.copy()


def get_template(theme: str = "lumix") -> str:
    """Get Plotly template for a given theme.

    Args:
        theme: Theme name

    Returns:
        Plotly template name string.

    Examples::

        template = get_template("dark")
        # Returns: 'plotly_dark'
    """
    return TEMPLATES.get(theme, TEMPLATES["default"])


__all__ = [
    "LUMIX_COLORS",
    "SEMANTIC_COLORS",
    "TEMPLATES",
    "get_color_sequence",
    "get_template",
]