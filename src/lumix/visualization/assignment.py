"""Assignment matrix visualization for assignment/allocation problems.

This module provides heatmap-style visualizations for assignment optimization
problems, showing resource-to-task allocations in a matrix format.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, TypeVar

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go, make_subplots

if TYPE_CHECKING:
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


@dataclass
class LXAssignmentCell:
    """Represents a cell in the assignment matrix.

    Attributes:
        row_id: Row identifier (e.g., worker ID).
        col_id: Column identifier (e.g., task ID).
        row_name: Display name for row.
        col_name: Display name for column.
        is_assigned: Whether this assignment is active.
        value: Value/cost of the assignment.
        metadata: Additional display metadata.

    Examples::

        cell = LXAssignmentCell(
            row_id="worker_1",
            col_id="task_1",
            row_name="Alice",
            col_name="Backend Dev",
            is_assigned=True,
            value=200,  # cost
        )
    """

    row_id: str
    col_id: str
    row_name: str
    col_name: str
    is_assigned: bool = False
    value: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LXAssignmentRow:
    """Represents a row entity (e.g., worker) with capacity info.

    Attributes:
        id: Unique identifier.
        name: Display name.
        capacity: Maximum assignments allowed.
        assigned_count: Number of current assignments.
        metadata: Additional display metadata.

    Examples::

        row = LXAssignmentRow(
            id="worker_1",
            name="Alice",
            capacity=3,
            assigned_count=2,
        )
    """

    id: str
    name: str
    capacity: int = 1
    assigned_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


class LXAssignmentMatrix(LXBaseVisualizer[TModel], Generic[TModel]):
    """Assignment matrix visualization for resource allocation problems.

    Creates interactive heatmap visualizations showing:

    - Resources (workers, machines) on Y-axis
    - Items (tasks, jobs) on X-axis
    - Colored cells indicating active assignments
    - Cost/value displayed in each assigned cell
    - Optional utilization sidebar

    Examples:
        Basic assignment visualization::

            rows = [
                LXAssignmentRow("w1", "Alice", capacity=3, assigned_count=2),
                LXAssignmentRow("w2", "Bob", capacity=4, assigned_count=3),
            ]

            cells = [
                LXAssignmentCell("w1", "t1", "Alice", "Task 1", True, 200),
                LXAssignmentCell("w1", "t2", "Alice", "Task 2", True, 150),
                LXAssignmentCell("w2", "t3", "Bob", "Task 3", True, 180),
            ]

            viz = LXAssignmentMatrix(rows, cells)
            viz.show()

        From solution with extraction function::

            viz = LXAssignmentMatrix.from_solution(
                solution,
                row_extractor=extract_workers,
                cell_extractor=extract_assignments,
            )
            viz.show()
    """

    def __init__(
        self,
        rows: List[LXAssignmentRow],
        cells: List[LXAssignmentCell],
        column_names: Optional[List[str]] = None,
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize assignment matrix visualizer.

        Args:
            rows: List of row entities (workers, resources).
            cells: List of assignment cells.
            column_names: Optional ordered list of column names.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.rows = rows
        self.cells = cells
        self._column_names = column_names
        self._show_utilization: bool = True
        self._value_format: str = "${:.0f}"
        self._title: str = "Assignment Matrix"
        self._row_label: str = "Resource"
        self._col_label: str = "Item"

    @classmethod
    def from_solution(
        cls,
        solution: "LXSolution[TModel]",
        row_extractor: Any,
        cell_extractor: Any,
        column_names: Optional[List[str]] = None,
        config: Optional[LXVisualizationConfig] = None,
    ) -> "LXAssignmentMatrix[TModel]":
        """Create assignment matrix from solution using extraction functions.

        Args:
            solution: Optimization solution.
            row_extractor: Function to extract rows from solution.
            cell_extractor: Function to extract cells from solution.
            column_names: Optional ordered list of column names.
            config: Visualization configuration.

        Returns:
            LXAssignmentMatrix instance.
        """
        rows = row_extractor(solution)
        cells = cell_extractor(solution)
        return cls(rows, cells, column_names, config)

    def set_title(self, title: str) -> Self:
        """Set the chart title.

        Args:
            title: Chart title text.

        Returns:
            Self for chaining.
        """
        self._title = title
        return self

    def set_labels(self, row_label: str, col_label: str) -> Self:
        """Set axis labels.

        Args:
            row_label: Label for Y-axis (rows).
            col_label: Label for X-axis (columns).

        Returns:
            Self for chaining.
        """
        self._row_label = row_label
        self._col_label = col_label
        return self

    def set_value_format(self, fmt: str) -> Self:
        """Set value format string.

        Args:
            fmt: Python format string (e.g., "${:.0f}", "{:.1f}h").

        Returns:
            Self for chaining.
        """
        self._value_format = fmt
        return self

    def show_utilization(self, show: bool = True) -> Self:
        """Toggle utilization sidebar.

        Args:
            show: Whether to show utilization chart.

        Returns:
            Self for chaining.
        """
        self._show_utilization = show
        return self

    def plot(self) -> Any:
        """Generate assignment matrix visualization.

        Returns:
            Plotly Figure.
        """
        if not self.rows or not self.cells:
            fig = go.Figure()
            fig.add_annotation(
                text="No assignment data to display",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        # Get row and column names
        row_names = [r.name for r in self.rows]
        row_ids = [r.id for r in self.rows]

        # Get unique column names from cells or use provided list
        if self._column_names:
            col_names = self._column_names
        else:
            col_names = list(dict.fromkeys(c.col_name for c in self.cells))

        # Build cell lookup
        cell_lookup: Dict[tuple, LXAssignmentCell] = {}
        for cell in self.cells:
            cell_lookup[(cell.row_id, cell.col_name)] = cell

        # Build matrix data
        matrix = []
        text_matrix = []

        for row in self.rows:
            row_data = []
            text_data = []
            for col_name in col_names:
                cell = cell_lookup.get((row.id, col_name))
                if cell and cell.is_assigned:
                    row_data.append(cell.value)
                    text_data.append(self._value_format.format(cell.value))
                else:
                    row_data.append(0)
                    text_data.append("")
            matrix.append(row_data)
            text_matrix.append(text_data)

        # Create figure
        if self._show_utilization:
            fig = make_subplots(
                rows=1,
                cols=2,
                column_widths=[0.75, 0.25],
                subplot_titles=(self._title, "Utilization"),
                specs=[[{"type": "heatmap"}, {"type": "bar"}]],
                horizontal_spacing=0.08,
            )
        else:
            fig = go.Figure()

        # Determine color range
        max_val = max((c.value for c in self.cells if c.is_assigned), default=1)
        if max_val == 0:
            max_val = 1

        # Add heatmap
        colors = self._get_colors()
        heatmap = go.Heatmap(
            z=matrix,
            x=col_names,
            y=row_names,
            text=text_matrix,
            texttemplate="%{text}",
            textfont={"size": 11, "color": "white"},
            colorscale=[
                [0, "#ecf0f1"],           # Not assigned (light gray)
                [0.001, colors[0]],       # Low value
                [0.5, colors[2]],         # Medium value
                [1, colors[3]],           # High value
            ],
            showscale=True,
            colorbar=dict(
                title="Value",
                x=0.68 if self._show_utilization else 1.02,
            ),
            hovertemplate=(
                "<b>%{y}</b> → <b>%{x}</b><br>"
                "Value: %{text}<extra></extra>"
            ),
        )

        if self._show_utilization:
            fig.add_trace(heatmap, row=1, col=1)
        else:
            fig.add_trace(heatmap)

        # Add utilization bar chart
        if self._show_utilization:
            utilization_pct = []
            bar_colors = []
            bar_text = []

            for row in self.rows:
                if row.capacity > 0:
                    pct = (row.assigned_count / row.capacity) * 100
                else:
                    pct = 0

                utilization_pct.append(pct)
                bar_text.append(f"{row.assigned_count}/{row.capacity}")

                # Color by utilization level
                if pct < 70:
                    bar_colors.append(colors[2])  # Green - low
                elif pct < 100:
                    bar_colors.append(colors[1])  # Orange - medium
                else:
                    bar_colors.append(colors[3])  # Red - at capacity

            fig.add_trace(
                go.Bar(
                    y=row_names,
                    x=utilization_pct,
                    orientation="h",
                    marker_color=bar_colors,
                    text=bar_text,
                    textposition="inside",
                    textfont=dict(color="white", size=10),
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Assigned: %{text}<br>"
                        "Utilization: %{x:.1f}%<extra></extra>"
                    ),
                    showlegend=False,
                ),
                row=1,
                col=2,
            )

            # Update axes
            fig.update_xaxes(title_text=self._col_label, row=1, col=1, tickangle=45)
            fig.update_yaxes(title_text=self._row_label, row=1, col=1)
            fig.update_xaxes(title_text="%", row=1, col=2, range=[0, 110])
            fig.update_yaxes(showticklabels=False, row=1, col=2)
        else:
            fig.update_xaxes(title_text=self._col_label, tickangle=45)
            fig.update_yaxes(title_text=self._row_label)

        # Calculate total
        total_value = sum(c.value for c in self.cells if c.is_assigned)

        # Update layout
        title_text = f"{self._title} (Total: {self._value_format.format(total_value)})"
        fig.update_layout(
            title=dict(text=title_text, x=0.5, xanchor="center"),
            margin=dict(t=80, b=80, l=100, r=60),
        )

        return self._apply_theme(fig)


__all__ = ["LXAssignmentMatrix", "LXAssignmentCell", "LXAssignmentRow"]