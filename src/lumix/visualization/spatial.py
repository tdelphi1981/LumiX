"""Spatial/geographic visualization for location problems.

This module provides X-Y coordinate visualizations for facility location,
network design, and other spatial optimization problems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Tuple, TypeVar, Union

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go

if TYPE_CHECKING:
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


@dataclass
class LXSpatialNode:
    """Represents a node (facility/customer) in spatial visualization.

    Attributes:
        id: Unique node identifier.
        name: Display name.
        x: X coordinate (longitude for geographic).
        y: Y coordinate (latitude for geographic).
        node_type: Type of node ('facility', 'customer', 'hub', etc.).
        is_active: Whether the node is active/open in the solution.
        value: Optional value associated with the node (capacity, demand, etc.).
        color: Optional color override.
        metadata: Additional display metadata.

    Examples::

        facility = LXSpatialNode(
            id="warehouse_1",
            name="New York Warehouse",
            x=-74.0060,
            y=40.7128,
            node_type="facility",
            is_active=True,
            value=500,  # capacity
        )
    """

    id: str
    name: str
    x: float
    y: float
    node_type: str = "default"
    is_active: bool = True
    value: Optional[float] = None
    color: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LXSpatialEdge:
    """Represents an edge (flow/connection) between nodes.

    Attributes:
        source_id: Source node identifier.
        target_id: Target node identifier.
        value: Flow value or connection weight.
        label: Optional edge label.
        color: Optional color override.
        metadata: Additional display metadata.

    Examples::

        edge = LXSpatialEdge(
            source_id="warehouse_1",
            target_id="customer_1",
            value=150.0,  # shipping quantity
        )
    """

    source_id: str
    target_id: str
    value: float = 1.0
    label: Optional[str] = None
    color: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LXSpatialMap(LXBaseVisualizer[TModel], Generic[TModel]):
    """Spatial/geographic visualization for location optimization problems.

    Creates interactive X-Y scatter plots showing:

    - Facility locations (with open/closed status)
    - Customer/demand locations
    - Flow connections between nodes
    - Geographic network structure

    Examples:
        Basic facility location visualization::

            # Create nodes for facilities
            facilities = [
                LXSpatialNode("w1", "Warehouse A", -74.0, 40.7, "facility", is_open),
                LXSpatialNode("w2", "Warehouse B", -118.2, 34.0, "facility", is_open),
            ]

            # Create nodes for customers
            customers = [
                LXSpatialNode("c1", "Customer 1", -75.0, 40.0, "customer"),
            ]

            # Create edges for flows
            edges = [
                LXSpatialEdge("w1", "c1", 150.0),
            ]

            viz = LXSpatialMap(facilities + customers, edges)
            viz.show()

        From solution with extraction functions::

            viz = LXSpatialMap.from_solution(
                solution,
                node_extractor=extract_nodes,
                edge_extractor=extract_edges,
            )
            viz.show()
    """

    def __init__(
        self,
        nodes: List[LXSpatialNode],
        edges: Optional[List[LXSpatialEdge]] = None,
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize spatial map visualizer.

        Args:
            nodes: List of nodes (facilities, customers, etc.).
            edges: Optional list of edges (flows, connections).
            config: Visualization configuration.
        """
        super().__init__(config)
        self.nodes = nodes
        self.edges = edges or []
        self._show_edges: bool = True
        self._edge_width_scale: float = 1.0
        self._node_size_scale: float = 1.0
        self._title: str = "Facility Location Map"

    @classmethod
    def from_solution(
        cls,
        solution: "LXSolution[TModel]",
        node_extractor: Any,
        edge_extractor: Optional[Any] = None,
        config: Optional[LXVisualizationConfig] = None,
    ) -> "LXSpatialMap[TModel]":
        """Create spatial map from solution using extraction functions.

        Args:
            solution: Optimization solution.
            node_extractor: Function to extract nodes from solution.
            edge_extractor: Optional function to extract edges from solution.
            config: Visualization configuration.

        Returns:
            LXSpatialMap instance.
        """
        nodes = node_extractor(solution)
        edges = edge_extractor(solution) if edge_extractor else []
        return cls(nodes, edges, config)

    def set_title(self, title: str) -> Self:
        """Set the chart title.

        Args:
            title: Chart title text.

        Returns:
            Self for chaining.
        """
        self._title = title
        return self

    def show_edges(self, show: bool = True) -> Self:
        """Toggle edge/flow display.

        Args:
            show: Whether to show edges.

        Returns:
            Self for chaining.
        """
        self._show_edges = show
        return self

    def set_edge_width_scale(self, scale: float) -> Self:
        """Set edge width scaling factor.

        Args:
            scale: Width multiplier (1.0 = default).

        Returns:
            Self for chaining.
        """
        self._edge_width_scale = scale
        return self

    def set_node_size_scale(self, scale: float) -> Self:
        """Set node size scaling factor.

        Args:
            scale: Size multiplier (1.0 = default).

        Returns:
            Self for chaining.
        """
        self._node_size_scale = scale
        return self

    def plot(self) -> Any:
        """Generate spatial map visualization.

        Returns:
            Plotly Figure.
        """
        if not self.nodes:
            fig = go.Figure()
            fig.add_annotation(
                text="No nodes to display",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        colors = self._get_colors()
        fig = go.Figure()

        # Create node lookup for edge drawing
        node_lookup = {node.id: node for node in self.nodes}

        # Draw edges first (so they appear behind nodes)
        if self._show_edges and self.edges:
            self._add_edges(fig, node_lookup, colors)

        # Draw nodes by type
        self._add_nodes(fig, colors)

        # Update layout
        fig.update_layout(
            title=dict(text=self._title, x=0.5, xanchor="center"),
            xaxis=dict(
                title="Longitude",
                scaleanchor="y",
                scaleratio=1,
            ),
            yaxis=dict(title="Latitude"),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
            margin=dict(t=80, b=60, l=60, r=60),
            hovermode="closest",
        )

        return self._apply_theme(fig)

    def _add_edges(
        self,
        fig: Any,
        node_lookup: Dict[str, LXSpatialNode],
        colors: List[str],
    ) -> None:
        """Add edge traces to figure."""
        # Calculate max flow for width scaling
        max_flow = max((e.value for e in self.edges), default=1.0)
        if max_flow == 0:
            max_flow = 1.0

        for edge in self.edges:
            source = node_lookup.get(edge.source_id)
            target = node_lookup.get(edge.target_id)

            if not source or not target:
                continue

            # Scale line width based on flow value
            width = max(1, (edge.value / max_flow) * 5 * self._edge_width_scale)

            # Build hover text
            hover_text = f"{source.name} → {target.name}<br>Flow: {edge.value:.1f}"
            if edge.metadata:
                for key, val in edge.metadata.items():
                    hover_text += f"<br>{key.title()}: {val}"

            fig.add_trace(
                go.Scatter(
                    x=[source.x, target.x],
                    y=[source.y, target.y],
                    mode="lines",
                    line=dict(
                        width=width,
                        color=edge.color or "#95a5a6",
                    ),
                    hoverinfo="text",
                    hovertext=hover_text,
                    showlegend=False,
                )
            )

            # Add flow label at midpoint
            if edge.value > 0:
                mid_x = (source.x + target.x) / 2
                mid_y = (source.y + target.y) / 2
                fig.add_annotation(
                    x=mid_x,
                    y=mid_y,
                    text=f"{edge.value:.0f}",
                    showarrow=False,
                    font=dict(size=9, color="#2c3e50"),
                    bgcolor="rgba(255,255,255,0.7)",
                )

    def _add_nodes(self, fig: Any, colors: List[str]) -> None:
        """Add node traces to figure."""
        # Group nodes by type
        nodes_by_type: Dict[str, List[LXSpatialNode]] = {}
        for node in self.nodes:
            key = node.node_type
            if key not in nodes_by_type:
                nodes_by_type[key] = []
            nodes_by_type[key].append(node)

        # Define marker styles for different node types
        type_styles = {
            "facility": {
                "symbol": "square",
                "size": 18,
                "active_color": colors[0],  # Blue for open
                "inactive_color": "#bdc3c7",  # Gray for closed
            },
            "customer": {
                "symbol": "circle",
                "size": 12,
                "active_color": colors[2],  # Green
                "inactive_color": colors[2],
            },
            "hub": {
                "symbol": "diamond",
                "size": 16,
                "active_color": colors[1],  # Orange
                "inactive_color": "#bdc3c7",
            },
            "default": {
                "symbol": "circle",
                "size": 10,
                "active_color": colors[0],
                "inactive_color": "#bdc3c7",
            },
        }

        for node_type, type_nodes in nodes_by_type.items():
            style = type_styles.get(node_type, type_styles["default"])

            # Split into active and inactive for facilities
            if node_type == "facility":
                active_nodes = [n for n in type_nodes if n.is_active]
                inactive_nodes = [n for n in type_nodes if not n.is_active]

                # Add inactive facilities (closed)
                if inactive_nodes:
                    self._add_node_trace(
                        fig,
                        inactive_nodes,
                        f"Closed {node_type.title()}",
                        style["symbol"],
                        style["size"] * self._node_size_scale,
                        style["inactive_color"],
                        line_color="#7f8c8d",
                    )

                # Add active facilities (open)
                if active_nodes:
                    self._add_node_trace(
                        fig,
                        active_nodes,
                        f"Open {node_type.title()}",
                        style["symbol"],
                        style["size"] * self._node_size_scale,
                        style["active_color"],
                        line_color="#2c3e50",
                    )
            else:
                # Add all nodes of this type
                self._add_node_trace(
                    fig,
                    type_nodes,
                    node_type.title(),
                    style["symbol"],
                    style["size"] * self._node_size_scale,
                    style["active_color"],
                    line_color="#2c3e50",
                )

    def _add_node_trace(
        self,
        fig: Any,
        nodes: List[LXSpatialNode],
        name: str,
        symbol: str,
        size: float,
        color: str,
        line_color: str,
    ) -> None:
        """Add a trace for a group of nodes."""
        x_coords = [n.x for n in nodes]
        y_coords = [n.y for n in nodes]
        names = [n.name for n in nodes]

        # Build hover text
        hover_texts = []
        for node in nodes:
            parts = [f"<b>{node.name}</b>"]
            if node.value is not None:
                parts.append(f"Value: {node.value:.1f}")
            if node.metadata:
                for key, val in node.metadata.items():
                    parts.append(f"{key.title()}: {val}")
            hover_texts.append("<br>".join(parts))

        fig.add_trace(
            go.Scatter(
                x=x_coords,
                y=y_coords,
                mode="markers+text",
                name=name,
                marker=dict(
                    symbol=symbol,
                    size=size,
                    color=color,
                    line=dict(width=2, color=line_color),
                ),
                text=names,
                textposition="top center",
                textfont=dict(size=10),
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hover_texts,
            )
        )


__all__ = ["LXSpatialMap", "LXSpatialNode", "LXSpatialEdge"]