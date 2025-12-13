"""Network graph visualization for model structure.

This module provides network graph visualizations showing the structure
of optimization models, including variable-constraint relationships.
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Set, Tuple, TypeVar

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go

if TYPE_CHECKING:
    from ..core.model import LXModel

TModel = TypeVar("TModel")


class LXModelGraph(LXBaseVisualizer[TModel], Generic[TModel]):
    """Network graph visualization showing model structure.

    Creates interactive network diagrams showing:

    - Variables as nodes
    - Constraints as edges or intermediate nodes
    - Variable-constraint dependencies
    - Objective function connections

    Examples:
        Basic usage::

            viz = LXModelGraph(model)
            viz.show()

        Customized layout::

            viz = (
                LXModelGraph(model)
                .set_layout("circular")
                .highlight_variables(["production", "inventory"])
            )
            viz.show()
    """

    def __init__(
        self,
        model: "LXModel[TModel]",
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize model graph visualizer.

        Args:
            model: Optimization model to visualize.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.model = model
        self._layout: str = "spring"
        self._highlighted_vars: Set[str] = set()
        self._show_constraints_as_nodes: bool = True

    def set_layout(self, layout: str) -> Self:
        """Set graph layout algorithm.

        Args:
            layout: Layout name ('spring', 'circular', 'hierarchical').

        Returns:
            Self for chaining.

        Examples::

            viz = viz.set_layout("circular")
        """
        self._layout = layout
        return self

    def highlight_variables(self, names: List[str]) -> Self:
        """Highlight specific variables.

        Args:
            names: Variable names to highlight.

        Returns:
            Self for chaining.
        """
        self._highlighted_vars = set(names)
        return self

    def constraints_as_nodes(self, as_nodes: bool = True) -> Self:
        """Show constraints as separate nodes (vs edges).

        Args:
            as_nodes: If True, constraints are nodes; if False, edges.

        Returns:
            Self for chaining.
        """
        self._show_constraints_as_nodes = as_nodes
        return self

    def plot(self) -> Any:
        """Generate network graph visualization.

        Returns:
            Plotly Figure.
        """
        # Get variable and constraint names
        var_names = [var.name for var in self.model.variables]
        constraint_names = [c.name for c in self.model.constraints]

        if not var_names and not constraint_names:
            fig = go.Figure()
            fig.add_annotation(
                text="Empty model",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        # Calculate positions
        positions = self._calculate_positions(var_names, constraint_names)
        colors = self._get_colors()

        fig = go.Figure()

        # Add edges (variable-constraint connections)
        edge_x: List[Optional[float]] = []
        edge_y: List[Optional[float]] = []

        for constraint in self.model.constraints:
            cx, cy = positions[constraint.name]
            # Connect to all variables (simplified - in reality would parse expression)
            for var in self.model.variables:
                vx, vy = positions[var.name]
                edge_x.extend([vx, cx, None])
                edge_y.extend([vy, cy, None])

        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(width=0.5, color="#888"),
                hoverinfo="none",
                showlegend=False,
            )
        )

        # Add variable nodes
        var_x = [positions[name][0] for name in var_names]
        var_y = [positions[name][1] for name in var_names]
        var_colors = [
            colors[2] if name in self._highlighted_vars else colors[0]
            for name in var_names
        ]

        fig.add_trace(
            go.Scatter(
                x=var_x,
                y=var_y,
                mode="markers+text",
                marker=dict(
                    size=20,
                    color=var_colors,
                    line=dict(width=2, color="white"),
                ),
                text=var_names,
                textposition="top center",
                name="Variables",
                hovertemplate="<b>Variable: %{text}</b><extra></extra>",
            )
        )

        # Add constraint nodes
        if self._show_constraints_as_nodes and constraint_names:
            const_x = [positions[name][0] for name in constraint_names]
            const_y = [positions[name][1] for name in constraint_names]

            fig.add_trace(
                go.Scatter(
                    x=const_x,
                    y=const_y,
                    mode="markers+text",
                    marker=dict(
                        size=15,
                        color=colors[1],
                        symbol="square",
                        line=dict(width=2, color="white"),
                    ),
                    text=constraint_names,
                    textposition="bottom center",
                    name="Constraints",
                    hovertemplate="<b>Constraint: %{text}</b><extra></extra>",
                )
            )

        fig.update_layout(
            title=f"Model Structure: {self.model.name}",
            showlegend=True,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )

        return self._apply_theme(fig)

    def plot_bipartite(self) -> Any:
        """Plot model as bipartite graph.

        Variables on left, constraints on right, edges showing relationships.

        Returns:
            Plotly Figure.
        """
        var_names = [var.name for var in self.model.variables]
        constraint_names = [c.name for c in self.model.constraints]
        colors = self._get_colors()

        fig = go.Figure()

        # Position variables on left
        n_vars = len(var_names)
        var_positions = {
            name: (-1, i - n_vars / 2) for i, name in enumerate(var_names)
        }

        # Position constraints on right
        n_const = len(constraint_names)
        const_positions = {
            name: (1, i - n_const / 2) for i, name in enumerate(constraint_names)
        }

        # Add edges
        edge_x: List[Optional[float]] = []
        edge_y: List[Optional[float]] = []

        for const_name in constraint_names:
            cx, cy = const_positions[const_name]
            for var_name in var_names:
                vx, vy = var_positions[var_name]
                edge_x.extend([vx, cx, None])
                edge_y.extend([vy, cy, None])

        fig.add_trace(
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(width=0.5, color="#ccc"),
                hoverinfo="none",
                showlegend=False,
            )
        )

        # Add variable nodes
        fig.add_trace(
            go.Scatter(
                x=[pos[0] for pos in var_positions.values()],
                y=[pos[1] for pos in var_positions.values()],
                mode="markers+text",
                marker=dict(size=15, color=colors[0]),
                text=list(var_positions.keys()),
                textposition="middle left",
                name="Variables",
            )
        )

        # Add constraint nodes
        fig.add_trace(
            go.Scatter(
                x=[pos[0] for pos in const_positions.values()],
                y=[pos[1] for pos in const_positions.values()],
                mode="markers+text",
                marker=dict(size=15, color=colors[1], symbol="square"),
                text=list(const_positions.keys()),
                textposition="middle right",
                name="Constraints",
            )
        )

        fig.update_layout(
            title=f"Model Structure (Bipartite): {self.model.name}",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        )

        return self._apply_theme(fig)

    def _calculate_positions(
        self,
        var_names: List[str],
        constraint_names: List[str],
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate node positions using selected layout."""
        positions: Dict[str, Tuple[float, float]] = {}

        if self._layout == "circular":
            # Variables on outer circle, constraints on inner
            n_vars = len(var_names)
            n_const = len(constraint_names)

            for i, name in enumerate(var_names):
                angle = 2 * math.pi * i / max(n_vars, 1)
                positions[name] = (2 * math.cos(angle), 2 * math.sin(angle))

            for i, name in enumerate(constraint_names):
                angle = 2 * math.pi * i / max(n_const, 1)
                positions[name] = (math.cos(angle), math.sin(angle))

        elif self._layout == "hierarchical":
            # Variables at top, constraints at bottom
            for i, name in enumerate(var_names):
                positions[name] = (i - len(var_names) / 2, 1)

            for i, name in enumerate(constraint_names):
                positions[name] = (i - len(constraint_names) / 2, -1)

        else:  # spring layout (default)
            # Simple spring-like positioning
            random.seed(42)

            for name in var_names:
                positions[name] = (
                    random.uniform(-1, 1),
                    random.uniform(0.5, 1.5),
                )

            for name in constraint_names:
                positions[name] = (
                    random.uniform(-1, 1),
                    random.uniform(-1.5, -0.5),
                )

        return positions


__all__ = ["LXModelGraph"]