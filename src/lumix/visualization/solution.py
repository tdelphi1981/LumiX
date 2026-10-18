"""Visualization for optimization solutions.

This module provides interactive visualizations for LXSolution objects,
including variable values, constraint utilization, and solution summaries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Sequence, TypeVar

from typing_extensions import Self

from ..core.enums import LXConstraintSense
from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go, make_subplots

if TYPE_CHECKING:
    from ..core.model import LXModel
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


class LXSolutionVisualizer(LXBaseVisualizer[TModel], Generic[TModel]):
    """Interactive visualization for optimization solutions.

    Creates charts showing:

    - Variable values (bar charts, waterfall)
    - Objective breakdown
    - Constraint utilization (capacity usage)
    - Solution summary dashboard

    Examples:
        Basic usage::

            solution = optimizer.solve(model)
            viz = LXSolutionVisualizer(solution, model)
            viz.show()

        Customized visualization::

            viz = (
                LXSolutionVisualizer(solution, model)
                .configure(theme="dark", width=1000)
                .filter_variables(["production", "inventory"])
                .sort_by("value", ascending=False)
            )
            viz.to_html("solution.html")

        Variable bar chart only::

            fig = viz.plot_variables()
            fig.show()
    """

    def __init__(
        self,
        solution: "LXSolution[TModel]",
        model: Optional["LXModel[TModel]"] = None,
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize solution visualizer.

        Args:
            solution: Optimization solution to visualize.
            model: Original model (optional, for constraint info).
            config: Visualization configuration.
        """
        super().__init__(config)
        self.solution = solution
        self.model = model
        self._variable_filter: Optional[List[str]] = None
        self._sort_by: str = "name"
        self._sort_ascending: bool = True
        self._min_value: float = 1e-6

    def filter_variables(self, names: Sequence[str]) -> Self:
        """Filter to show only specified variables.

        Args:
            names: Variable names to include.

        Returns:
            Self for chaining.

        Examples::

            viz = viz.filter_variables(["production", "inventory"])
        """
        self._variable_filter = list(names)
        return self

    def sort_by(
        self,
        key: str = "value",
        ascending: bool = True,
    ) -> Self:
        """Sort variables for display.

        Args:
            key: Sort key ('name', 'value', 'absolute').
            ascending: Sort order.

        Returns:
            Self for chaining.

        Examples::

            viz = viz.sort_by("value", ascending=False)  # Highest first
        """
        self._sort_by = key
        self._sort_ascending = ascending
        return self

    def hide_zero_values(self, threshold: float = 1e-6) -> Self:
        """Hide variables with values below threshold.

        Args:
            threshold: Minimum absolute value to display.

        Returns:
            Self for chaining.
        """
        self._min_value = threshold
        return self

    def plot(self) -> Any:
        """Generate comprehensive solution visualization.

        Creates a multi-panel figure with:
        - Variable values bar chart
        - Solution summary indicator
        - Constraint utilization (if model available)
        - Value distribution histogram

        Returns:
            Plotly Figure with subplots showing solution overview.
        """
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Variable Values",
                "",  # No subtitle for indicator (it has its own title)
                "Constraint Status",
                "Value Distribution",
            ),
            specs=[
                [{"type": "bar"}, {"type": "indicator"}],
                [{"type": "bar"}, {"type": "histogram"}],
            ],
            horizontal_spacing=0.12,
            vertical_spacing=0.15,
        )

        # Add variable values bar chart
        self._add_variables_trace(fig, row=1, col=1)

        # Add solution summary indicator
        self._add_summary_indicator(fig, row=1, col=2)

        # Add constraint status
        self._add_constraint_status(fig, row=2, col=1)

        # Add value distribution histogram
        self._add_value_distribution(fig, row=2, col=2)

        if self.solution.is_feasible():
            title = (f"Solution: {self.solution.status} "
                     f"(Objective: {self.solution.objective_value:,.2f})")
        else:
            title = f"Solution: no solution ({self.solution.status})"

        fig.update_layout(
            title=dict(text=title, x=0.5, xanchor="center"),
            showlegend=False,
            margin=dict(t=80, b=60, l=60, r=60),
        )

        # Update axis labels for clarity
        fig.update_xaxes(title_text="Variable", row=1, col=1)
        fig.update_yaxes(title_text="Value", row=1, col=1)
        fig.update_xaxes(title_text="Status", row=2, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_xaxes(title_text="Value", row=2, col=2)
        fig.update_yaxes(title_text="Frequency", row=2, col=2)

        return self._apply_theme(fig)

    def plot_variables(
        self,
        chart_type: str = "bar",
        orientation: str = "v",
    ) -> Any:
        """Plot variable values.

        Args:
            chart_type: Chart type ('bar' or 'waterfall').
            orientation: Bar orientation ('v' or 'h').

        Returns:
            Plotly Figure.

        Examples::

            fig = viz.plot_variables(orientation="h")
            fig.show()
        """
        data = self._get_variable_data()
        colors = self._get_colors()

        if chart_type == "bar":
            if orientation == "v":
                fig = go.Figure(
                    go.Bar(
                        x=data["names"],
                        y=data["values"],
                        marker_color=colors[0],
                        text=[f"{v:.2f}" for v in data["values"]],
                        textposition="auto",
                    )
                )
            else:
                fig = go.Figure(
                    go.Bar(
                        y=data["names"],
                        x=data["values"],
                        orientation="h",
                        marker_color=colors[0],
                        text=[f"{v:.2f}" for v in data["values"]],
                        textposition="auto",
                    )
                )
        elif chart_type == "waterfall":
            fig = go.Figure(
                go.Waterfall(
                    name="Variables",
                    x=data["names"],
                    y=data["values"],
                    textposition="auto",
                    text=[f"{v:.2f}" for v in data["values"]],
                )
            )
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

        fig.update_layout(
            title="Variable Values",
            xaxis_title="Variable" if orientation == "v" else "Value",
            yaxis_title="Value" if orientation == "v" else "Variable",
        )
        return self._apply_theme(fig)

    def plot_constraint_utilization(self) -> Any:
        """Plot how much of each constraint's right-hand side is used (horizontal bars).

        Each bar is ``100 * LHS / RHS`` of one row, evaluated at the solution; binding
        rows (zero slack) are coloured apart. Requires the model; duals are optional
        and shown in the hover text.

        Returns:
            Plotly Figure showing constraint capacity usage.

        Raises:
            ValueError: If the visualizer was created without the model.

        .. versionchanged:: 0.3.0
           Bars show LHS / RHS of each row; it used to draw every non-binding row at
           50 % and required duals.
        """
        if self.model is None:
            raise ValueError(
                "plot_constraint_utilization needs the model: "
                "LXSolutionVisualizer(solution, model)"
            )
        from ..solution.activity import row_activity

        rows = []
        for name, act in row_activity(self.model, self.solution).items():
            if act.sense == LXConstraintSense.LE and act.rhs > 0:
                util = 100.0 * act.lhs / act.rhs
            else:
                util = None          # % of the right-hand side means nothing here
            rows.append({"name": name, "act": act, "util": util,
                         "shadow": self.solution.shadow_prices.get(name)})

        fig = go.Figure()
        colors = self._get_colors()
        for label, group, color in (
            ("Binding", [r for r in rows if r["act"].binding], colors[3]),
            ("Non-binding", [r for r in rows if not r["act"].binding], colors[4]),
        ):
            if not group:
                continue
            fig.add_trace(go.Bar(
                y=[r["name"] for r in group],
                x=[r["util"] for r in group],
                orientation="h",
                name=label,
                marker_color=color,
                customdata=[[r["act"].lhs, r["act"].rhs, r["act"].slack,
                             "-" if r["shadow"] is None else f"{r['shadow']:.4g}"]
                            for r in group],
                hovertemplate=(
                    "<b>%{y}</b><br>Utilization: %{x:.1f}%<br>LHS: %{customdata[0]:.4g}"
                    "<br>RHS: %{customdata[1]:.4g}<br>Slack: %{customdata[2]:.4g}"
                    "<br>Shadow price: %{customdata[3]}<extra></extra>"
                ),
            ))
        fig.update_layout(
            title="Constraint Utilization",
            xaxis_title="Utilization (% of a positive <= right-hand side)",
            yaxis_title="Constraint",
            barmode="overlay",
        )
        return self._apply_theme(fig)

    def _get_variable_data(self) -> Dict[str, List[Any]]:
        """Extract and process variable data for plotting."""
        names: List[str] = []
        values: List[float] = []

        for var_name, var_value in self.solution.variables.items():
            # Apply filter
            if self._variable_filter and var_name not in self._variable_filter:
                continue

            if isinstance(var_value, dict):
                # Indexed variable - flatten
                for idx, val in var_value.items():
                    if abs(val) >= self._min_value:
                        names.append(f"{var_name}[{idx}]")
                        values.append(float(val))
            else:
                if abs(var_value) >= self._min_value:
                    names.append(var_name)
                    values.append(float(var_value))

        # Sort
        if names:
            if self._sort_by == "value":
                sorted_pairs = sorted(
                    zip(names, values),
                    key=lambda x: x[1],
                    reverse=not self._sort_ascending,
                )
            elif self._sort_by == "absolute":
                sorted_pairs = sorted(
                    zip(names, values),
                    key=lambda x: abs(x[1]),
                    reverse=not self._sort_ascending,
                )
            else:  # name
                sorted_pairs = sorted(
                    zip(names, values),
                    key=lambda x: x[0],
                    reverse=not self._sort_ascending,
                )
            names, values = map(list, zip(*sorted_pairs))

        return {"names": names, "values": values}

    def _add_variables_trace(self, fig: Any, row: int, col: int) -> None:
        """Add variable values trace to subplot."""
        data = self._get_variable_data()
        colors = self._get_colors()

        # Limit for readability
        max_items = 15
        names = data["names"][:max_items]
        values = data["values"][:max_items]

        fig.add_trace(
            go.Bar(
                x=names,
                y=values,
                marker_color=colors[0],
                text=[f"{v:.1f}" for v in values],
                textposition="outside",
                hovertemplate="<b>%{x}</b><br>Value: %{y:,.2f}<extra></extra>",
            ),
            row=row,
            col=col,
        )

    def _add_summary_indicator(self, fig: Any, row: int, col: int) -> None:
        """Add solution summary indicator."""
        # Format status for display
        status = self.solution.status.upper() if self.solution.status else "UNKNOWN"
        status_color = "#2ecc71" if "optimal" in status.lower() else "#e74c3c"

        fig.add_trace(
            go.Indicator(
                mode="number",
                value=self.solution.objective_value if self.solution.is_feasible() else None,
                title={
                    "text": f"<b>Objective Value{'' if self.solution.is_feasible() else ': No solution'}</b><br><span style='font-size:14px;color:{status_color}'>{status}</span>",
                    "font": {"size": 16},
                },
                number={
                    "font": {"size": 40, "color": "#2c3e50"},
                    "valueformat": ",.2f",
                },
                domain={"row": row - 1, "column": col - 1},
            ),
            row=row,
            col=col,
        )

    def _add_constraint_status(self, fig: Any, row: int, col: int) -> None:
        """Add constraint status chart."""
        colors = self._get_colors()

        activity: Dict[str, Any] = {}
        if self.model is not None:
            from ..solution.activity import row_activity

            activity = row_activity(self.model, self.solution)
        if activity:
            # binding = zero slack, as LXConstraintSensitivity.is_binding
            binding_count = sum(1 for act in activity.values() if act.binding)
            non_binding_count = len(activity) - binding_count
        elif self.solution.shadow_prices:
            binding_count = sum(
                1 for sp in self.solution.shadow_prices.values() if abs(sp) > 1e-6
            )
            non_binding_count = len(self.solution.shadow_prices) - binding_count
        if activity or self.solution.shadow_prices:

            fig.add_trace(
                go.Bar(
                    x=["Binding", "Non-binding"],
                    y=[binding_count, non_binding_count],
                    marker_color=[colors[3], colors[4]],
                    text=[binding_count, non_binding_count],
                    textposition="auto",
                ),
                row=row,
                col=col,
            )
        else:
            # No shadow prices - show placeholder bar with message
            fig.add_trace(
                go.Bar(
                    x=["No Data"],
                    y=[0],
                    marker_color=["#bdc3c7"],
                    showlegend=False,
                ),
                row=row,
                col=col,
            )
            # Add annotation centered in the subplot area
            fig.add_annotation(
                text="<i>Enable sensitivity analysis<br>for constraint data</i>",
                xref="x domain",
                yref="y domain",
                x=0.5,
                y=0.5,
                xanchor="center",
                yanchor="middle",
                showarrow=False,
                font=dict(size=11, color="#7f8c8d"),
                row=row,
                col=col,
            )

    def _add_value_distribution(self, fig: Any, row: int, col: int) -> None:
        """Add variable value distribution histogram."""
        data = self._get_variable_data()
        colors = self._get_colors()

        if data["values"]:
            # Determine appropriate number of bins
            n_values = len(data["values"])
            n_bins = min(max(5, n_values // 2), 15)

            fig.add_trace(
                go.Histogram(
                    x=data["values"],
                    nbinsx=n_bins,
                    marker_color=colors[0],
                    marker_line_color="#2c3e50",
                    marker_line_width=1,
                    hovertemplate="Range: %{x}<br>Count: %{y}<extra></extra>",
                ),
                row=row,
                col=col,
            )


__all__ = ["LXSolutionVisualizer"]