"""
LumiX Visualization Module
===========================

Interactive visualization tools for optimization results.

This module provides Plotly-based interactive charts for:

- **Solution Analysis**: Variable values, constraint utilization
- **Sensitivity Analysis**: Tornado charts, shadow prices, binding constraints
- **Scenario Comparison**: Multi-scenario bar charts, sensitivity curves
- **Goal Programming**: Achievement gauges, deviation analysis
- **Scheduling**: Gantt charts for assignment/scheduling problems
- **Model Structure**: Network graphs showing variable-constraint relationships
- **Dashboards**: Combined overview dashboards

Installation
------------
Visualization requires optional dependencies::

    pip install lumix-opt[viz]

Quick Start
-----------
Basic solution visualization::

    from lumix import LXModel, LXOptimizer
    from lumix.visualization import LXSolutionVisualizer

    model = build_my_model()
    solution = LXOptimizer().use_solver("ortools").solve(model)

    viz = LXSolutionVisualizer(solution, model)
    viz.show()  # Opens in browser/Jupyter

Export to HTML::

    viz.to_html("solution.html")

Sensitivity analysis::

    from lumix.visualization import LXSensitivityPlot
    from lumix import LXSensitivityAnalyzer

    analyzer = LXSensitivityAnalyzer(model, solution)
    viz = LXSensitivityPlot(analyzer)
    viz.plot_tornado(top_n=15).show()

Combined dashboard::

    from lumix.visualization import LXDashboard

    dashboard = LXDashboard(model, solution)
    dashboard.add_sensitivity(analyzer)
    dashboard.to_html("dashboard.html")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ._compat import _PLOTLY_AVAILABLE, require_viz_dependencies

# Export availability check
__all__ = [
    # Availability flags
    "_PLOTLY_AVAILABLE",
    "require_viz_dependencies",
    # Configuration
    "LXVisualizationConfig",
    # Solution
    "LXSolutionVisualizer",
    # Sensitivity
    "LXSensitivityPlot",
    # Scenarios
    "LXScenarioCompare",
    # Goals
    "LXGoalProgressChart",
    # Scheduling
    "LXScheduleGantt",
    "LXScheduleTask",
    # Model graph
    "LXModelGraph",
    # Dashboard
    "LXDashboard",
    # Themes
    "LUMIX_COLORS",
    "get_color_sequence",
]


def __getattr__(name: str) -> object:
    """Lazy import visualization classes to avoid import errors.

    This allows importing from lumix.visualization even when
    plotly is not installed - the ImportError is only raised
    when actually trying to use a visualization class.
    """
    if name == "LXVisualizationConfig":
        from ._base import LXVisualizationConfig

        return LXVisualizationConfig

    if name == "LXSolutionVisualizer":
        require_viz_dependencies()
        from .solution import LXSolutionVisualizer

        return LXSolutionVisualizer

    if name == "LXSensitivityPlot":
        require_viz_dependencies()
        from .sensitivity import LXSensitivityPlot

        return LXSensitivityPlot

    if name == "LXScenarioCompare":
        require_viz_dependencies()
        from .scenario import LXScenarioCompare

        return LXScenarioCompare

    if name == "LXGoalProgressChart":
        require_viz_dependencies()
        from .goals import LXGoalProgressChart

        return LXGoalProgressChart

    if name == "LXScheduleGantt":
        require_viz_dependencies()
        from .schedule import LXScheduleGantt

        return LXScheduleGantt

    if name == "LXScheduleTask":
        from .schedule import LXScheduleTask

        return LXScheduleTask

    if name == "LXModelGraph":
        require_viz_dependencies()
        from .graph import LXModelGraph

        return LXModelGraph

    if name == "LXDashboard":
        require_viz_dependencies()
        from .dashboard import LXDashboard

        return LXDashboard

    if name == "LUMIX_COLORS":
        from .themes import LUMIX_COLORS

        return LUMIX_COLORS

    if name == "get_color_sequence":
        from .themes import get_color_sequence

        return get_color_sequence

    raise AttributeError(f"module 'lumix.visualization' has no attribute '{name}'")