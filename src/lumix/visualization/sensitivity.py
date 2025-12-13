"""Sensitivity analysis visualization.

This module provides interactive visualizations for sensitivity analysis
results, including tornado charts, shadow prices, and binding constraints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, List, Optional, TypeVar

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go, make_subplots

if TYPE_CHECKING:
    from ..analysis.sensitivity import LXSensitivityAnalyzer

TModel = TypeVar("TModel")


class LXSensitivityPlot(LXBaseVisualizer[TModel], Generic[TModel]):
    """Interactive visualization for sensitivity analysis results.

    Creates charts showing:

    - Tornado charts for shadow prices
    - Reduced cost waterfall
    - Binding constraint indicators
    - Sensitivity ranges (when available)

    Examples:
        Basic usage::

            analyzer = LXSensitivityAnalyzer(model, solution)
            viz = LXSensitivityPlot(analyzer)
            viz.show()

        Tornado chart only::

            fig = viz.plot_tornado(top_n=10)
            fig.show()

        Export to HTML::

            viz.configure(width=1200).to_html("sensitivity.html")
    """

    def __init__(
        self,
        analyzer: "LXSensitivityAnalyzer[TModel]",
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize sensitivity visualizer.

        Args:
            analyzer: Sensitivity analyzer with computed results.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.analyzer = analyzer
        self._top_n: int = 15

    def top_n(self, n: int) -> Self:
        """Limit number of items shown.

        Args:
            n: Maximum items to display.

        Returns:
            Self for chaining.

        Examples::

            viz = viz.top_n(20)
        """
        self._top_n = n
        return self

    def plot(self) -> Any:
        """Generate comprehensive sensitivity visualization.

        Creates a multi-panel figure with:
        - Tornado chart of shadow prices
        - Binding vs non-binding pie chart
        - Reduced costs bar chart
        - Bottleneck impact visualization

        Returns:
            Plotly Figure with sensitivity analysis overview.
        """
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Shadow Prices (Tornado Chart)",
                "Binding vs Non-binding Constraints",
                "Reduced Costs",
                "Bottleneck Impact",
            ),
            specs=[
                [{"type": "bar"}, {"type": "pie"}],
                [{"type": "bar"}, {"type": "bar"}],
            ],
        )

        # Tornado chart
        self._add_tornado_trace(fig, row=1, col=1)

        # Binding constraint pie
        self._add_binding_pie(fig, row=1, col=2)

        # Reduced costs
        self._add_reduced_costs_trace(fig, row=2, col=1)

        # Bottleneck impact
        self._add_bottleneck_trace(fig, row=2, col=2)

        fig.update_layout(
            title="Sensitivity Analysis Overview",
            showlegend=True,
        )

        return self._apply_theme(fig)

    def plot_tornado(
        self,
        top_n: Optional[int] = None,
        show_positive: bool = True,
        show_negative: bool = True,
    ) -> Any:
        """Create tornado chart of shadow prices.

        Tornado charts show parameters sorted by impact magnitude,
        with bars extending left (negative) and right (positive).

        Args:
            top_n: Number of items to show (default: configured top_n).
            show_positive: Show positive shadow prices.
            show_negative: Show negative shadow prices.

        Returns:
            Plotly Figure.

        Examples::

            fig = viz.plot_tornado(top_n=15)
            fig.show()
        """
        n = top_n or self._top_n
        top_constraints = self.analyzer.get_most_sensitive_constraints(top_n=n)
        colors = self._get_colors()

        names: List[str] = []
        positive_values: List[float] = []
        negative_values: List[float] = []

        for name, sens in reversed(top_constraints):
            if sens.shadow_price is None:
                continue
            names.append(name)
            if sens.shadow_price >= 0:
                positive_values.append(sens.shadow_price if show_positive else 0)
                negative_values.append(0)
            else:
                positive_values.append(0)
                negative_values.append(sens.shadow_price if show_negative else 0)

        fig = go.Figure()

        # Positive bars (right side)
        fig.add_trace(
            go.Bar(
                y=names,
                x=positive_values,
                orientation="h",
                name="Positive Impact",
                marker_color=colors[4],  # Green
                hovertemplate="<b>%{y}</b><br>Shadow Price: %{x:.4f}<extra></extra>",
            )
        )

        # Negative bars (left side)
        fig.add_trace(
            go.Bar(
                y=names,
                x=negative_values,
                orientation="h",
                name="Negative Impact",
                marker_color=colors[3],  # Red
                hovertemplate="<b>%{y}</b><br>Shadow Price: %{x:.4f}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Shadow Prices - Tornado Chart",
            xaxis_title="Shadow Price ($/unit)",
            yaxis_title="Constraint",
            barmode="relative",
            bargap=0.3,
        )

        return self._apply_theme(fig)

    def plot_binding_constraints(self) -> Any:
        """Plot binding constraints with their shadow prices.

        Creates a horizontal bar chart showing all binding constraints
        and their shadow prices, sorted by magnitude.

        Returns:
            Plotly Figure showing binding constraints.
        """
        binding = self.analyzer.get_binding_constraints()
        colors = self._get_colors()

        if not binding:
            fig = go.Figure()
            fig.add_annotation(
                text="No binding constraints found",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        # Sort by absolute shadow price
        sorted_binding = sorted(
            binding.items(),
            key=lambda x: abs(x[1].shadow_price or 0),
            reverse=True,
        )

        names = [name for name, _ in sorted_binding]
        shadow_prices = [sens.shadow_price or 0 for _, sens in sorted_binding]

        bar_colors = [
            colors[3] if sp > 0 else colors[2] for sp in shadow_prices
        ]

        fig = go.Figure(
            go.Bar(
                y=names,
                x=shadow_prices,
                orientation="h",
                marker_color=bar_colors,
                text=[f"${sp:.2f}" for sp in shadow_prices],
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Shadow Price: $%{x:.4f}/unit<extra></extra>",
            )
        )

        fig.update_layout(
            title="Binding Constraints",
            xaxis_title="Shadow Price ($/unit)",
            yaxis_title="Constraint",
        )

        return self._apply_theme(fig)

    def plot_reduced_costs(self, top_n: Optional[int] = None) -> Any:
        """Plot variable reduced costs.

        Shows reduced costs for variables, which represent the
        opportunity cost of forcing a variable to increase.

        Args:
            top_n: Number of variables to show.

        Returns:
            Plotly Figure.
        """
        n = top_n or self._top_n
        top_vars = self.analyzer.get_most_sensitive_variables(top_n=n)
        colors = self._get_colors()

        names = [name for name, _ in top_vars]
        costs = [sens.reduced_cost or 0 for _, sens in top_vars]
        at_bound = [sens.is_at_bound for _, sens in top_vars]

        bar_colors = [colors[3] if bound else colors[0] for bound in at_bound]

        fig = go.Figure(
            go.Bar(
                x=names,
                y=costs,
                marker_color=bar_colors,
                text=[f"${c:.4f}" for c in costs],
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Reduced Cost: $%{y:.4f}<extra></extra>",
            )
        )

        fig.update_layout(
            title="Variable Reduced Costs",
            xaxis_title="Variable",
            yaxis_title="Reduced Cost ($)",
        )

        return self._apply_theme(fig)

    def plot_bottleneck_summary(self) -> Any:
        """Plot bottleneck constraints summary.

        Shows identified bottleneck constraints (binding constraints
        with significant shadow prices) ranked by impact.

        Returns:
            Plotly Figure.
        """
        bottlenecks = self.analyzer.identify_bottlenecks()
        colors = self._get_colors()

        if not bottlenecks:
            fig = go.Figure()
            fig.add_annotation(
                text="No bottlenecks identified",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        # Get shadow prices for bottlenecks
        data = []
        for name in bottlenecks:
            sens = self.analyzer.analyze_constraint(name)
            data.append((name, abs(sens.shadow_price or 0)))

        # Sort by impact
        data.sort(key=lambda x: x[1], reverse=True)
        names, impacts = zip(*data) if data else ([], [])

        fig = go.Figure(
            go.Bar(
                x=list(names),
                y=list(impacts),
                marker_color=colors[3],
                text=[f"${imp:.2f}" for imp in impacts],
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Impact: $%{y:.4f}/unit<extra></extra>",
            )
        )

        fig.update_layout(
            title=f"Bottleneck Constraints ({len(bottlenecks)} identified)",
            xaxis_title="Constraint",
            yaxis_title="Shadow Price Magnitude ($/unit)",
        )

        return self._apply_theme(fig)

    def _add_tornado_trace(self, fig: Any, row: int, col: int) -> None:
        """Add tornado chart trace to subplot."""
        top_constraints = self.analyzer.get_most_sensitive_constraints(top_n=10)
        colors = self._get_colors()

        names = [name for name, _ in reversed(top_constraints)]
        values = [sens.shadow_price or 0 for _, sens in reversed(top_constraints)]

        bar_colors = [colors[4] if v >= 0 else colors[3] for v in values]

        fig.add_trace(
            go.Bar(
                y=names,
                x=values,
                orientation="h",
                marker_color=bar_colors,
            ),
            row=row,
            col=col,
        )

    def _add_binding_pie(self, fig: Any, row: int, col: int) -> None:
        """Add binding/non-binding pie chart."""
        all_constraints = self.analyzer.analyze_all_constraints()
        colors = self._get_colors()

        binding_count = sum(1 for sens in all_constraints.values() if sens.is_binding)
        non_binding_count = len(all_constraints) - binding_count

        fig.add_trace(
            go.Pie(
                labels=["Binding", "Non-binding"],
                values=[binding_count, non_binding_count],
                marker_colors=[colors[3], colors[4]],
            ),
            row=row,
            col=col,
        )

    def _add_reduced_costs_trace(self, fig: Any, row: int, col: int) -> None:
        """Add reduced costs bar chart."""
        top_vars = self.analyzer.get_most_sensitive_variables(top_n=10)
        colors = self._get_colors()

        names = [name for name, _ in top_vars]
        costs = [sens.reduced_cost or 0 for _, sens in top_vars]

        fig.add_trace(
            go.Bar(
                x=names,
                y=costs,
                marker_color=colors[0],
            ),
            row=row,
            col=col,
        )

    def _add_bottleneck_trace(self, fig: Any, row: int, col: int) -> None:
        """Add bottleneck impact visualization."""
        bottlenecks = self.analyzer.identify_bottlenecks()
        colors = self._get_colors()

        if bottlenecks:
            data = []
            for name in bottlenecks[:10]:
                sens = self.analyzer.analyze_constraint(name)
                data.append((name, abs(sens.shadow_price or 0)))

            data.sort(key=lambda x: x[1], reverse=True)
            if data:
                names, impacts = zip(*data)

                fig.add_trace(
                    go.Bar(
                        x=list(names),
                        y=list(impacts),
                        marker_color=colors[3],
                    ),
                    row=row,
                    col=col,
                )


__all__ = ["LXSensitivityPlot"]