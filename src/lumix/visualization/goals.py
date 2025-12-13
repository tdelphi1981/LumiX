"""Goal programming visualization.

This module provides interactive visualizations for goal programming
results, including goal satisfaction status and deviation analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, List, Optional, TypeVar

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go, make_subplots

if TYPE_CHECKING:
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


class LXGoalProgressChart(LXBaseVisualizer[TModel], Generic[TModel]):
    """Interactive visualization for goal programming results.

    Creates charts showing:

    - Goal satisfaction status (achieved/missed)
    - Deviation analysis (positive/negative)
    - Priority-weighted progress
    - Goal achievement heatmap

    Examples:
        Basic usage::

            solution = optimizer.solve(goal_model)
            viz = LXGoalProgressChart(solution)
            viz.show()

        Deviation analysis::

            fig = viz.plot_deviations()
            fig.show()

        Achievement gauge::

            fig = viz.plot_achievement_gauge()
            fig.show()
    """

    def __init__(
        self,
        solution: "LXSolution[TModel]",
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize goal progress visualizer.

        Args:
            solution: Solution with goal programming results.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.solution = solution
        self._tolerance: float = 1e-6

    def set_tolerance(self, tolerance: float) -> Self:
        """Set tolerance for goal satisfaction check.

        Args:
            tolerance: Deviation tolerance for satisfaction.

        Returns:
            Self for chaining.
        """
        self._tolerance = tolerance
        return self

    def plot(self) -> Any:
        """Generate comprehensive goal programming visualization.

        Creates a multi-panel figure with:
        - Goal achievement pie chart
        - Total deviations by goal
        - Positive vs negative deviations
        - Overall progress gauge

        Returns:
            Plotly Figure with goal progress overview.
        """
        if not self.solution.goal_deviations:
            fig = go.Figure()
            fig.add_annotation(
                text="No goal programming data in solution",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Goal Achievement Status",
                "Total Deviations by Goal",
                "Positive vs Negative Deviations",
                "Goal Satisfaction Progress",
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "bar"}, {"type": "indicator"}],
            ],
        )

        # Achievement pie chart
        self._add_achievement_pie(fig, row=1, col=1)

        # Total deviation bars
        self._add_deviation_bars(fig, row=1, col=2)

        # Positive vs negative comparison
        self._add_pos_neg_comparison(fig, row=2, col=1)

        # Overall progress gauge
        self._add_progress_gauge(fig, row=2, col=2)

        fig.update_layout(
            title="Goal Programming Results",
            showlegend=True,
        )

        return self._apply_theme(fig)

    def plot_satisfaction_status(self, tolerance: Optional[float] = None) -> Any:
        """Plot goal satisfaction status as traffic light indicators.

        Each goal is shown with a color indicating its status:
        - Green: Satisfied (deviation within tolerance)
        - Orange: Partially met (small deviation)
        - Red: Not met (large deviation)

        Args:
            tolerance: Deviation tolerance for satisfaction.

        Returns:
            Plotly Figure.
        """
        tol = tolerance or self._tolerance
        colors = self._get_colors()

        goals = list(self.solution.goal_deviations.keys())
        statuses: List[str] = []
        bar_colors: List[str] = []

        for goal_name in goals:
            is_satisfied = self.solution.is_goal_satisfied(goal_name, tol)
            total_dev = self.solution.get_total_deviation(goal_name) or 0

            if is_satisfied:
                statuses.append("Satisfied")
                bar_colors.append(colors[4])  # Green
            elif total_dev < 10:  # Small deviation
                statuses.append("Partially Met")
                bar_colors.append(colors[2])  # Orange
            else:
                statuses.append("Not Met")
                bar_colors.append(colors[3])  # Red

        fig = go.Figure(
            go.Bar(
                x=goals,
                y=[1] * len(goals),  # Equal height
                marker_color=bar_colors,
                text=statuses,
                textposition="inside",
                hovertemplate="<b>%{x}</b><br>Status: %{text}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Goal Satisfaction Status",
            xaxis_title="Goal",
            yaxis_visible=False,
            showlegend=False,
        )

        return self._apply_theme(fig)

    def plot_deviations(self, stacked: bool = True) -> Any:
        """Plot positive and negative deviations for each goal.

        Shows the deviation from target for each goal, split into
        positive (over-target) and negative (under-target) components.

        Args:
            stacked: Stack positive and negative bars.

        Returns:
            Plotly Figure.
        """
        colors = self._get_colors()

        goals: List[str] = []
        pos_devs: List[float] = []
        neg_devs: List[float] = []

        for goal_name, deviations in self.solution.goal_deviations.items():
            goals.append(goal_name)

            pos = deviations.get("pos", 0)
            neg = deviations.get("neg", 0)

            # Handle dict values (indexed goals)
            if isinstance(pos, dict):
                pos = sum(pos.values())
            if isinstance(neg, dict):
                neg = sum(neg.values())

            pos_devs.append(float(pos))
            neg_devs.append(float(neg))

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                name="Positive Deviation (Over-target)",
                x=goals,
                y=pos_devs,
                marker_color=colors[2],  # Orange
                hovertemplate="<b>%{x}</b><br>Over-target: %{y:.2f}<extra></extra>",
            )
        )

        fig.add_trace(
            go.Bar(
                name="Negative Deviation (Under-target)",
                x=goals,
                y=neg_devs,
                marker_color=colors[5],  # Purple
                hovertemplate="<b>%{x}</b><br>Under-target: %{y:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Goal Deviations Analysis",
            xaxis_title="Goal",
            yaxis_title="Deviation",
            barmode="stack" if stacked else "group",
        )

        return self._apply_theme(fig)

    def plot_achievement_gauge(self) -> Any:
        """Gauge chart showing overall goal achievement percentage.

        Shows what percentage of goals are satisfied within the
        configured tolerance.

        Returns:
            Plotly Figure.
        """
        colors = self._get_colors()

        total_goals = len(self.solution.goal_deviations)
        satisfied = sum(
            1
            for name in self.solution.goal_deviations
            if self.solution.is_goal_satisfied(name, self._tolerance)
        )

        percentage = (satisfied / total_goals * 100) if total_goals > 0 else 0

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=percentage,
                title={"text": f"Goals Achieved ({satisfied}/{total_goals})"},
                delta={"reference": 100},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": colors[0]},
                    "steps": [
                        {"range": [0, 50], "color": colors[3]},
                        {"range": [50, 80], "color": colors[2]},
                        {"range": [80, 100], "color": colors[4]},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 4},
                        "thickness": 0.75,
                        "value": percentage,
                    },
                },
            )
        )

        fig.update_layout(title="Overall Goal Achievement")

        return self._apply_theme(fig)

    def plot_deviation_waterfall(self) -> Any:
        """Waterfall chart showing cumulative goal deviations.

        Shows how each goal's deviation contributes to the total
        deviation from targets.

        Returns:
            Plotly Figure.
        """
        goals: List[str] = []
        total_devs: List[float] = []

        for goal_name in self.solution.goal_deviations:
            goals.append(goal_name)
            total_devs.append(self.solution.get_total_deviation(goal_name) or 0)

        # Add total
        goals.append("Total")
        total_devs.append(sum(total_devs[:-1]) if total_devs else 0)

        measure = ["relative"] * (len(goals) - 1) + ["total"]

        fig = go.Figure(
            go.Waterfall(
                name="Deviation",
                orientation="v",
                measure=measure,
                x=goals,
                y=total_devs,
                text=[f"{d:.2f}" for d in total_devs],
                textposition="outside",
            )
        )

        fig.update_layout(
            title="Cumulative Goal Deviations",
            xaxis_title="Goal",
            yaxis_title="Deviation",
        )

        return self._apply_theme(fig)

    def _add_achievement_pie(self, fig: Any, row: int, col: int) -> None:
        """Add achievement status pie chart."""
        colors = self._get_colors()

        total = len(self.solution.goal_deviations)
        satisfied = sum(
            1
            for name in self.solution.goal_deviations
            if self.solution.is_goal_satisfied(name, self._tolerance)
        )

        fig.add_trace(
            go.Pie(
                labels=["Satisfied", "Not Satisfied"],
                values=[satisfied, total - satisfied],
                marker_colors=[colors[4], colors[3]],
            ),
            row=row,
            col=col,
        )

    def _add_deviation_bars(self, fig: Any, row: int, col: int) -> None:
        """Add total deviation bars."""
        colors = self._get_colors()

        goals: List[str] = []
        total_devs: List[float] = []

        for name in self.solution.goal_deviations:
            goals.append(name)
            total_devs.append(self.solution.get_total_deviation(name) or 0)

        fig.add_trace(
            go.Bar(
                x=goals[:10],
                y=total_devs[:10],
                marker_color=colors[0],
            ),
            row=row,
            col=col,
        )

    def _add_pos_neg_comparison(self, fig: Any, row: int, col: int) -> None:
        """Add positive vs negative deviation comparison."""
        colors = self._get_colors()
        goals = list(self.solution.goal_deviations.keys())[:10]

        pos_trace_added = False
        neg_trace_added = False

        for goal_name in goals:
            devs = self.solution.goal_deviations[goal_name]
            pos = devs.get("pos", 0)
            neg = devs.get("neg", 0)

            if isinstance(pos, dict):
                pos = sum(pos.values())
            if isinstance(neg, dict):
                neg = sum(neg.values())

            fig.add_trace(
                go.Bar(
                    x=[goal_name],
                    y=[pos],
                    name="Positive" if not pos_trace_added else None,
                    marker_color=colors[2],
                    showlegend=not pos_trace_added,
                    legendgroup="positive",
                ),
                row=row,
                col=col,
            )
            pos_trace_added = True

            fig.add_trace(
                go.Bar(
                    x=[goal_name],
                    y=[neg],
                    name="Negative" if not neg_trace_added else None,
                    marker_color=colors[5],
                    showlegend=not neg_trace_added,
                    legendgroup="negative",
                ),
                row=row,
                col=col,
            )
            neg_trace_added = True

    def _add_progress_gauge(self, fig: Any, row: int, col: int) -> None:
        """Add overall progress gauge."""
        total = len(self.solution.goal_deviations)
        satisfied = sum(
            1
            for name in self.solution.goal_deviations
            if self.solution.is_goal_satisfied(name, self._tolerance)
        )
        pct = (satisfied / total * 100) if total > 0 else 0

        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=pct,
                gauge={"axis": {"range": [0, 100]}},
            ),
            row=row,
            col=col,
        )


__all__ = ["LXGoalProgressChart"]