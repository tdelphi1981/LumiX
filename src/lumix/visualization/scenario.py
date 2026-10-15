"""Scenario comparison visualization.

This module provides interactive visualizations for scenario analysis
results, including comparison charts and sensitivity curves.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Tuple, TypeVar

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go, make_subplots

if TYPE_CHECKING:
    from ..analysis.scenario import LXScenarioAnalyzer
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


def _ranked_feasible(analyzer: Any) -> List[Tuple[str, Any]]:
    """Feasible scenario results, best first in the sense the base model is solved."""
    from ..analysis._sense import solved_sense
    from ..core.enums import LXObjectiveSense

    feasible = [(n, s) for n, s in analyzer.results.items() if s.is_feasible()]
    maximize = solved_sense(analyzer.base_model) == LXObjectiveSense.MAXIMIZE
    return sorted(feasible, key=lambda item: item[1].objective_value, reverse=maximize)


class LXScenarioCompare(LXBaseVisualizer[TModel], Generic[TModel]):
    """Interactive visualization for scenario analysis comparison.

    Creates charts showing:

    - Scenario objective comparison (bar/radar)
    - Parameter sensitivity curves
    - Decision variable changes across scenarios
    - Scenario ranking table

    Examples:
        Basic usage::

            analyzer = LXScenarioAnalyzer(model, optimizer)
            analyzer.add_scenario(scenario1)
            analyzer.add_scenario(scenario2)
            analyzer.run_all_scenarios()

            viz = LXScenarioCompare(analyzer)
            viz.show()

        Specific visualizations::

            fig = viz.plot_comparison_bar()
            fig = viz.plot_sensitivity_curve("capacity", [0.8, 1.0, 1.2])
    """

    def __init__(
        self,
        analyzer: "LXScenarioAnalyzer[TModel]",
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize scenario comparison visualizer.

        Args:
            analyzer: Scenario analyzer with computed results.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.analyzer = analyzer

    def plot(self) -> Any:
        """Generate comprehensive scenario comparison visualization.

        Creates a multi-panel figure with:
        - Objective value comparison bars
        - Scenario ranking table
        - Percentage change from baseline
        - Decision variable comparison

        Returns:
            Plotly Figure with scenario overview.
        """
        if not self.analyzer.results:
            fig = go.Figure()
            fig.add_annotation(
                text="No scenario results. Run scenarios first.",
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
                "Objective Value Comparison",
                "Scenario Ranking",
                "% Change from Baseline",
                "Decision Variable Comparison",
            ),
            specs=[
                [{"type": "bar"}, {"type": "table"}],
                [{"type": "bar"}, {"type": "bar"}],
            ],
        )

        # Objective comparison bars
        self._add_objective_comparison(fig, row=1, col=1)

        # Ranking table
        self._add_ranking_table(fig, row=1, col=2)

        # Percentage change from baseline
        self._add_percentage_change(fig, row=2, col=1)

        # Variable comparison
        self._add_variable_comparison(fig, row=2, col=2)

        fig.update_layout(
            title="Scenario Analysis Comparison",
            showlegend=True,
        )

        return self._apply_theme(fig)

    def plot_comparison_bar(
        self,
        include_baseline: bool = True,
        sort_by_value: bool = True,
    ) -> Any:
        """Bar chart comparing scenario objective values.

        Args:
            include_baseline: Include baseline scenario.
            sort_by_value: Sort bars by objective value.

        Returns:
            Plotly Figure.

        Examples::

            fig = viz.plot_comparison_bar(sort_by_value=True)
            fig.show()
        """
        results = self.analyzer.results.copy()

        if not include_baseline and "baseline" in results:
            del results["baseline"]

        items = list(results.items())
        if sort_by_value:
            ranked = [(n, sol) for n, sol in _ranked_feasible(self.analyzer) if n in results]
            items = ranked + [(n, sol) for n, sol in items if not sol.is_feasible()]

        names = [name for name, _ in items]
        objectives = [sol.objective_value for _, sol in items]
        statuses = [sol.status for _, sol in items]
        colors = self._get_colors()

        # Color code by status
        bar_colors: List[str] = []
        for status in statuses:
            if "optimal" in status.lower():
                bar_colors.append(colors[4])  # Green
            elif "feasible" in status.lower():
                bar_colors.append(colors[2])  # Orange
            else:
                bar_colors.append(colors[3])  # Red

        fig = go.Figure(
            go.Bar(
                x=names,
                y=objectives,
                marker_color=bar_colors,
                text=[f"{obj:,.4g}" for obj in objectives],
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Objective: %{y:,.4g}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Scenario Objective Comparison",
            xaxis_title="Scenario",
            yaxis_title="Objective Value",
        )

        # Highlight best scenario
        if objectives:
            best_idx = objectives.index(max(objectives))
            fig.add_annotation(
                x=names[best_idx],
                y=objectives[best_idx],
                text="Best",
                showarrow=True,
                arrowhead=2,
                yshift=10,
            )

        return self._apply_theme(fig)

    def plot_radar_comparison(
        self,
        metrics: Optional[List[str]] = None,
    ) -> Any:
        """Radar chart comparing scenarios across multiple metrics.

        Args:
            metrics: List of metrics to compare (default: objective, solve_time).

        Returns:
            Plotly Figure.
        """
        if metrics is None:
            metrics = ["Objective", "Solve Time", "Gap"]

        fig = go.Figure()
        colors = self._get_colors()

        # Get max values for normalization
        max_obj = max(
            (s.objective_value for s in self.analyzer.results.values()),
            default=1,
        )
        max_time = max(
            (s.solve_time for s in self.analyzer.results.values()),
            default=1,
        )

        for i, (name, solution) in enumerate(self.analyzer.results.items()):
            values = [
                solution.objective_value / max_obj if max_obj else 0,
                1 - (solution.solve_time / max_time if max_time else 0),
                1 - (solution.gap or 0),
            ]
            # Close the radar polygon
            values.append(values[0])
            categories = metrics + [metrics[0]]

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    name=name,
                    fill="toself",
                    line_color=colors[i % len(colors)],
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            title="Scenario Comparison Radar",
        )

        return self._apply_theme(fig)

    def plot_sensitivity_curve(
        self,
        parameter_name: str,
        values: List[float],
        results: Optional[Dict[float, "LXSolution[TModel]"]] = None,
    ) -> Any:
        """Line chart showing sensitivity to a parameter.

        Args:
            parameter_name: Parameter name.
            values: Parameter values tested.
            results: Pre-computed sensitivity results (optional).

        Returns:
            Plotly Figure.

        Examples::

            fig = viz.plot_sensitivity_curve(
                "capacity",
                [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
            )
            fig.show()
        """
        if results is None:
            results = self.analyzer.sensitivity_to_parameter(parameter_name, values)

        x_values = list(results.keys())
        y_values = [sol.objective_value for sol in results.values()]
        colors = self._get_colors()

        fig = go.Figure(
            go.Scatter(
                x=x_values,
                y=y_values,
                mode="lines+markers",
                line=dict(color=colors[0], width=2),
                marker=dict(size=8),
                hovertemplate="<b>%{x:.2f}</b><br>Objective: %{y:,.4g}<extra></extra>",
            )
        )

        fig.update_layout(
            title=f"Sensitivity to {parameter_name}",
            xaxis_title=f"{parameter_name} Multiplier",
            yaxis_title="Objective Value",
        )

        return self._apply_theme(fig)

    def plot_scenario_waterfall(self) -> Any:
        """Bar chart of each scenario's objective against the baseline.

        Each scenario is a bar from the baseline objective to its own objective (not
        cumulative). Infeasible scenarios are left out and named in the title.

        Returns:
            Plotly Figure.

        .. versionchanged:: 0.3.0
           Bars are absolute against the baseline; they used to accumulate, and
           infeasible scenarios were drawn with an objective of 0.
        """
        if "baseline" not in self.analyzer.results:
            fig = go.Figure()
            fig.add_annotation(
                text="Baseline required for waterfall chart",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
            )
            return self._apply_theme(fig)

        baseline_val = self.analyzer.results["baseline"].objective_value
        names, bases, heights, labels = ["Baseline"], [0.0], [baseline_val], [f"{baseline_val:,.4g}"]
        skipped = []
        for name, sol in self.analyzer.results.items():
            if name == "baseline":
                continue
            if not sol.is_feasible():
                skipped.append(name)
                continue
            delta = sol.objective_value - baseline_val
            names.append(name)
            bases.append(baseline_val)
            heights.append(delta)
            labels.append(f"{delta:+,.4g}")
        colors = self._get_colors()
        bar_colors = [colors[0]] + [colors[4] if h >= 0 else colors[3] for h in heights[1:]]
        fig = go.Figure(go.Bar(
            x=names, y=heights, base=bases, text=labels, textposition="outside",
            marker_color=bar_colors, name="Scenario Impact",
        ))
        fig.add_hline(y=baseline_val, line_dash="dot")
        title = "Scenario Impact vs Baseline"
        if skipped:
            title += f" (infeasible: {', '.join(skipped)})"
        fig.update_layout(title=title, yaxis_title="Objective Value")
        return self._apply_theme(fig)

    def _add_objective_comparison(self, fig: Any, row: int, col: int) -> None:
        """Add objective comparison bars to subplot."""
        colors = self._get_colors()

        items = _ranked_feasible(self.analyzer)

        names = [name for name, _ in items][:10]
        objectives = [sol.objective_value for _, sol in items][:10]

        fig.add_trace(
            go.Bar(
                x=names,
                y=objectives,
                marker_color=colors[0],
            ),
            row=row,
            col=col,
        )

    def _add_ranking_table(self, fig: Any, row: int, col: int) -> None:
        """Add scenario ranking table."""
        items = _ranked_feasible(self.analyzer)

        baseline_obj = self.analyzer.results.get("baseline")
        baseline_val = baseline_obj.objective_value if baseline_obj else None

        ranks = list(range(1, len(items) + 1))
        names = [name for name, _ in items]
        objectives = [f"{sol.objective_value:,.2f}" for _, sol in items]
        changes: List[str] = []

        for _, sol in items:
            if baseline_val:
                pct = ((sol.objective_value - baseline_val) / baseline_val) * 100
                changes.append(f"{pct:+.1f}%")
            else:
                changes.append("-")

        fig.add_trace(
            go.Table(
                header=dict(
                    values=["Rank", "Scenario", "Objective", "vs Baseline"],
                    fill_color="paleturquoise",
                    align="left",
                ),
                cells=dict(
                    values=[ranks[:5], names[:5], objectives[:5], changes[:5]],
                    fill_color="lavender",
                    align="left",
                ),
            ),
            row=row,
            col=col,
        )

    def _add_percentage_change(self, fig: Any, row: int, col: int) -> None:
        """Add percentage change from baseline chart."""
        baseline = self.analyzer.results.get("baseline")
        if not baseline:
            return

        baseline_val = baseline.objective_value
        colors = self._get_colors()

        changes: List[float] = []
        names: List[str] = []

        for name, sol in self.analyzer.results.items():
            if name == "baseline":
                continue
            pct = ((sol.objective_value - baseline_val) / baseline_val) * 100
            changes.append(pct)
            names.append(name)

        # Sort by change
        if names and changes:
            sorted_pairs = sorted(zip(names, changes), key=lambda x: x[1], reverse=True)
            names, changes = map(list, zip(*sorted_pairs))

        bar_colors = [colors[4] if c >= 0 else colors[3] for c in changes]

        fig.add_trace(
            go.Bar(
                x=list(names)[:10],
                y=list(changes)[:10],
                marker_color=bar_colors[:10],
            ),
            row=row,
            col=col,
        )

    def _add_variable_comparison(self, fig: Any, row: int, col: int) -> None:
        """Add variable comparison across scenarios."""
        colors = self._get_colors()

        if not self.analyzer.results:
            return

        # Get first variable from first solution
        first_solution = next(iter(self.analyzer.results.values()))
        first_var = next(iter(first_solution.variables.keys()), None)

        if first_var is None:
            return

        # Compare first variable across scenarios
        names: List[str] = []
        values: List[float] = []

        for name, sol in self.analyzer.results.items():
            var_val = sol.variables.get(first_var, 0)
            if isinstance(var_val, dict):
                var_val = sum(var_val.values())
            names.append(name)
            values.append(float(var_val))

        fig.add_trace(
            go.Bar(
                x=names[:10],
                y=values[:10],
                marker_color=colors[1],
                name=first_var,
            ),
            row=row,
            col=col,
        )


__all__ = ["LXScenarioCompare"]