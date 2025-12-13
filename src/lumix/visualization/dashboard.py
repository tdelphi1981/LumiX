"""Combined dashboard visualization.

This module provides a comprehensive dashboard that combines multiple
visualization components into a single interactive view.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, List, Optional, Tuple, TypeVar

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go, make_subplots

if TYPE_CHECKING:
    from ..analysis.scenario import LXScenarioAnalyzer
    from ..analysis.sensitivity import LXSensitivityAnalyzer
    from ..core.model import LXModel
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


class LXDashboard(LXBaseVisualizer[TModel], Generic[TModel]):
    """Combined interactive dashboard for optimization results.

    Creates a comprehensive dashboard combining:

    - Solution overview
    - Sensitivity analysis
    - Goal programming progress (if applicable)
    - Key metrics and KPIs

    Examples:
        Basic usage::

            dashboard = LXDashboard(model, solution)
            dashboard.show()

        With all analyzers::

            sensitivity = LXSensitivityAnalyzer(model, solution)
            scenario = LXScenarioAnalyzer(model, optimizer)

            dashboard = (
                LXDashboard(model, solution)
                .add_sensitivity(sensitivity)
                .add_scenarios(scenario)
            )
            dashboard.to_html("dashboard.html")
    """

    def __init__(
        self,
        model: "LXModel[TModel]",
        solution: "LXSolution[TModel]",
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize dashboard.

        Args:
            model: Optimization model.
            solution: Solution to visualize.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.model = model
        self.solution = solution
        self._sensitivity_analyzer: Optional["LXSensitivityAnalyzer[TModel]"] = None
        self._scenario_analyzer: Optional["LXScenarioAnalyzer[TModel]"] = None
        self._custom_panels: List[Tuple[str, Any]] = []

    def add_sensitivity(
        self,
        analyzer: "LXSensitivityAnalyzer[TModel]",
    ) -> Self:
        """Add sensitivity analysis to dashboard.

        Args:
            analyzer: Sensitivity analyzer.

        Returns:
            Self for chaining.
        """
        self._sensitivity_analyzer = analyzer
        return self

    def add_scenarios(
        self,
        analyzer: "LXScenarioAnalyzer[TModel]",
    ) -> Self:
        """Add scenario analysis to dashboard.

        Args:
            analyzer: Scenario analyzer with results.

        Returns:
            Self for chaining.
        """
        self._scenario_analyzer = analyzer
        return self

    def add_custom_panel(self, title: str, figure: Any) -> Self:
        """Add custom Plotly figure to dashboard.

        Args:
            title: Panel title.
            figure: Plotly Figure.

        Returns:
            Self for chaining.
        """
        self._custom_panels.append((title, figure))
        return self

    def plot(self) -> Any:
        """Generate comprehensive dashboard.

        Creates a multi-panel figure combining all available data:
        - Solution summary and variables
        - Sensitivity analysis (if available)
        - Goal programming (if applicable)
        - Scenario comparison (if available)

        Returns:
            Plotly Figure with all panels.
        """
        # Determine grid size based on components
        has_goals = bool(self.solution.goal_deviations)
        has_sensitivity = self._sensitivity_analyzer is not None
        has_scenarios = self._scenario_analyzer is not None

        # Build subplot configuration
        n_rows = 2
        if has_sensitivity:
            n_rows = 3
        if has_goals:
            n_rows = max(n_rows, 3)
        if has_scenarios:
            n_rows = max(n_rows, 3)

        subplot_titles = ["Solution Summary", "Variable Values"]
        specs: List[List[dict]] = [[{"type": "indicator"}, {"type": "bar"}]]

        if has_sensitivity:
            subplot_titles.extend(["Shadow Prices (Top 10)", "Binding Constraints"])
            specs.append([{"type": "bar"}, {"type": "pie"}])

        if has_goals:
            subplot_titles.extend(["Goal Achievement", "Goal Deviations"])
            specs.append([{"type": "pie"}, {"type": "bar"}])

        if has_scenarios:
            subplot_titles.extend(["Scenario Comparison", "Best Scenarios"])
            if len(specs) < 4:
                specs.append([{"type": "bar"}, {"type": "table"}])

        fig = make_subplots(
            rows=n_rows,
            cols=2,
            subplot_titles=subplot_titles[:n_rows * 2],
            specs=specs[:n_rows],
        )

        # Row 1: Solution overview
        self._add_solution_summary(fig, row=1, col=1)
        self._add_variable_bars(fig, row=1, col=2)

        # Row 2: Sensitivity (if available)
        current_row = 2
        if has_sensitivity:
            self._add_sensitivity_panels(fig, row=current_row)
            current_row += 1

        # Row 3: Goals (if available)
        if has_goals:
            self._add_goal_panels(fig, row=current_row)
            current_row += 1

        # Row 4: Scenarios (if available)
        if has_scenarios and current_row <= n_rows:
            self._add_scenario_panels(fig, row=current_row)

        fig.update_layout(
            title=f"Optimization Dashboard: {self.model.name}",
            height=self.config.height * n_rows // 2,
            showlegend=True,
        )

        return self._apply_theme(fig)

    def plot_summary_only(self) -> Any:
        """Generate summary-only dashboard.

        A compact dashboard showing just the key metrics.

        Returns:
            Plotly Figure.
        """
        fig = make_subplots(
            rows=1,
            cols=3,
            subplot_titles=("Objective", "Status", "Solve Time"),
            specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        )

        colors = self._get_colors()

        # Objective
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=self.solution.objective_value,
                title={"text": "Objective Value"},
                number={"prefix": "$", "valueformat": ",.0f"},
            ),
            row=1,
            col=1,
        )

        # Status indicator
        status_color = colors[4] if self.solution.is_optimal() else colors[2]
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=100 if self.solution.is_optimal() else 0,
                title={"text": f"Status: {self.solution.status}"},
                delta={"reference": 100},
            ),
            row=1,
            col=2,
        )

        # Solve time
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=self.solution.solve_time,
                title={"text": "Solve Time"},
                number={"suffix": "s", "valueformat": ".3f"},
            ),
            row=1,
            col=3,
        )

        fig.update_layout(
            title=f"Solution Summary: {self.model.name}",
            height=300,
        )

        return self._apply_theme(fig)

    def _add_solution_summary(self, fig: Any, row: int, col: int) -> None:
        """Add solution summary indicator."""
        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=self.solution.objective_value,
                title={"text": f"Objective ({self.solution.status})"},
                number={"prefix": "$", "valueformat": ",.0f"},
            ),
            row=row,
            col=col,
        )

    def _add_variable_bars(self, fig: Any, row: int, col: int) -> None:
        """Add variable values bar chart."""
        colors = self._get_colors()

        # Get variable data
        names: List[str] = []
        values: List[float] = []

        for var_name, var_value in self.solution.variables.items():
            if isinstance(var_value, dict):
                for idx, val in list(var_value.items())[:5]:
                    if abs(val) > 1e-6:
                        names.append(f"{var_name}[{idx}]")
                        values.append(float(val))
            else:
                if abs(var_value) > 1e-6:
                    names.append(var_name)
                    values.append(float(var_value))

        # Sort by value
        if names:
            sorted_pairs = sorted(zip(names, values), key=lambda x: x[1], reverse=True)
            names, values = map(list, zip(*sorted_pairs))

        fig.add_trace(
            go.Bar(
                x=names[:15],
                y=values[:15],
                marker_color=colors[0],
            ),
            row=row,
            col=col,
        )

    def _add_sensitivity_panels(self, fig: Any, row: int) -> None:
        """Add sensitivity analysis panels."""
        if self._sensitivity_analyzer is None:
            return

        colors = self._get_colors()

        # Shadow prices bar
        top_constraints = self._sensitivity_analyzer.get_most_sensitive_constraints(top_n=10)
        names = [name for name, _ in top_constraints]
        values = [sens.shadow_price or 0 for _, sens in top_constraints]

        fig.add_trace(
            go.Bar(
                x=names,
                y=values,
                marker_color=colors[1],
            ),
            row=row,
            col=1,
        )

        # Binding constraints pie
        all_constraints = self._sensitivity_analyzer.analyze_all_constraints()
        binding = sum(1 for sens in all_constraints.values() if sens.is_binding)

        fig.add_trace(
            go.Pie(
                labels=["Binding", "Non-binding"],
                values=[binding, len(all_constraints) - binding],
                marker_colors=[colors[3], colors[4]],
            ),
            row=row,
            col=2,
        )

    def _add_goal_panels(self, fig: Any, row: int) -> None:
        """Add goal programming panels."""
        colors = self._get_colors()

        # Achievement pie
        total = len(self.solution.goal_deviations)
        satisfied = sum(
            1
            for name in self.solution.goal_deviations
            if self.solution.is_goal_satisfied(name)
        )

        fig.add_trace(
            go.Pie(
                labels=["Satisfied", "Not Satisfied"],
                values=[satisfied, total - satisfied],
                marker_colors=[colors[4], colors[3]],
            ),
            row=row,
            col=1,
        )

        # Deviations bar
        goals = list(self.solution.goal_deviations.keys())[:10]
        devs = [self.solution.get_total_deviation(g) or 0 for g in goals]

        fig.add_trace(
            go.Bar(
                x=goals,
                y=devs,
                marker_color=colors[2],
            ),
            row=row,
            col=2,
        )

    def _add_scenario_panels(self, fig: Any, row: int) -> None:
        """Add scenario comparison panels."""
        if self._scenario_analyzer is None or not self._scenario_analyzer.results:
            return

        colors = self._get_colors()

        # Scenario comparison bar
        items = sorted(
            self._scenario_analyzer.results.items(),
            key=lambda x: x[1].objective_value,
            reverse=True,
        )

        names = [name for name, _ in items][:10]
        objectives = [sol.objective_value for _, sol in items][:10]

        fig.add_trace(
            go.Bar(
                x=names,
                y=objectives,
                marker_color=colors[0],
            ),
            row=row,
            col=1,
        )

        # Best scenarios table
        ranks = list(range(1, min(6, len(items) + 1)))
        top_names = [name for name, _ in items][:5]
        top_objectives = [f"${sol.objective_value:,.0f}" for _, sol in items][:5]

        fig.add_trace(
            go.Table(
                header=dict(
                    values=["Rank", "Scenario", "Objective"],
                    fill_color="paleturquoise",
                ),
                cells=dict(
                    values=[ranks, top_names, top_objectives],
                    fill_color="lavender",
                ),
            ),
            row=row,
            col=2,
        )


__all__ = ["LXDashboard"]