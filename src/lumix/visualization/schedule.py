"""Gantt chart visualization for scheduling problems.

This module provides Gantt chart visualizations for scheduling optimization
problems, including task assignments and resource utilization.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Callable, Dict, Generic, List, Optional, TypeVar, Union

from typing_extensions import Self

from ._base import LXBaseVisualizer, LXVisualizationConfig
from ._compat import go

if TYPE_CHECKING:
    from ..solution.solution import LXSolution

TModel = TypeVar("TModel")


@dataclass
class LXScheduleTask:
    """Represents a task for Gantt chart visualization.

    Attributes:
        id: Unique task identifier.
        name: Display name.
        resource: Resource/machine/worker assigned.
        start: Start time (datetime or numeric).
        end: End time (datetime or numeric).
        color: Optional color override.
        metadata: Additional display metadata.

    Examples::

        task = LXScheduleTask(
            id="job1_machine1",
            name="Job 1",
            resource="Machine A",
            start=0,
            end=5,
        )
    """

    id: str
    name: str
    resource: str
    start: Union[datetime, float, int]
    end: Union[datetime, float, int]
    color: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LXScheduleGantt(LXBaseVisualizer[TModel], Generic[TModel]):
    """Gantt chart visualization for scheduling optimization results.

    Creates interactive Gantt charts showing:

    - Task assignments across resources/machines
    - Timeline with zoom and pan
    - Resource utilization overlays
    - Task details on hover

    Examples:
        From solution with extraction function::

            def extract_tasks(solution):
                tasks = []
                for (job, machine), value in solution.variables["assign"].items():
                    if value > 0.5:
                        tasks.append(LXScheduleTask(
                            id=f"{job}_{machine}",
                            name=f"Job {job}",
                            resource=f"Machine {machine}",
                            start=solution.variables["start"][(job, machine)],
                            end=solution.variables["end"][(job, machine)],
                        ))
                return tasks

            viz = LXScheduleGantt.from_solution(solution, extract_tasks)
            viz.show()

        From task list::

            tasks = [
                LXScheduleTask("1", "Task A", "Worker 1", 0, 5),
                LXScheduleTask("2", "Task B", "Worker 2", 2, 8),
            ]
            viz = LXScheduleGantt(tasks)
            viz.show()
    """

    def __init__(
        self,
        tasks: List[LXScheduleTask],
        config: Optional[LXVisualizationConfig] = None,
    ) -> None:
        """Initialize Gantt chart visualizer.

        Args:
            tasks: List of tasks to display.
            config: Visualization configuration.
        """
        super().__init__(config)
        self.tasks = tasks
        self._show_resource_utilization: bool = False
        self._time_unit: str = "hours"

    @classmethod
    def from_solution(
        cls,
        solution: "LXSolution[TModel]",
        task_extractor: Callable[["LXSolution[TModel]"], List[LXScheduleTask]],
        config: Optional[LXVisualizationConfig] = None,
    ) -> "LXScheduleGantt[TModel]":
        """Create Gantt chart from solution using extraction function.

        Args:
            solution: Optimization solution.
            task_extractor: Function to extract tasks from solution.
            config: Visualization configuration.

        Returns:
            LXScheduleGantt instance.

        Examples::

            def extract(sol):
                return [LXScheduleTask(...) for ... in sol.variables["assign"].items()]

            viz = LXScheduleGantt.from_solution(solution, extract)
        """
        tasks = task_extractor(solution)
        return cls(tasks, config)

    def show_resource_utilization(self, show: bool = True) -> Self:
        """Toggle resource utilization overlay.

        Args:
            show: Whether to show utilization.

        Returns:
            Self for chaining.
        """
        self._show_resource_utilization = show
        return self

    def set_time_unit(self, unit: str) -> Self:
        """Set time unit for display.

        Args:
            unit: Time unit ('hours', 'days', 'minutes').

        Returns:
            Self for chaining.
        """
        self._time_unit = unit
        return self

    def plot(self) -> Any:
        """Generate Gantt chart visualization.

        Returns:
            Plotly Figure.
        """
        if not self.tasks:
            fig = go.Figure()
            fig.add_annotation(
                text="No tasks to display",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font_size=16,
            )
            return self._apply_theme(fig)

        # Get unique resources for y-axis
        resources = list(set(task.resource for task in self.tasks))
        colors = self._get_colors()

        fig = go.Figure()

        # Add task bars
        for i, task in enumerate(self.tasks):
            color = task.color or colors[i % len(colors)]

            # Handle both datetime and numeric
            if isinstance(task.start, datetime):
                x_start = task.start
                x_end = task.end
                if isinstance(task.end, datetime):
                    duration = (task.end - task.start).total_seconds() / 3600
                else:
                    duration = 0
            else:
                x_start = task.start
                x_end = task.end
                duration = float(task.end) - float(task.start)

            # Width of bar
            width = float(x_end) - float(x_start) if isinstance(x_start, (int, float)) else duration

            fig.add_trace(
                go.Bar(
                    x=[width],
                    y=[task.resource],
                    base=[x_start],
                    orientation="h",
                    name=task.name,
                    marker_color=color,
                    text=task.name,
                    textposition="inside",
                    hovertemplate=(
                        f"<b>{task.name}</b><br>"
                        f"Resource: {task.resource}<br>"
                        f"Start: {x_start}<br>"
                        f"End: {x_end}<br>"
                        f"Duration: {duration:.1f} {self._time_unit}<extra></extra>"
                    ),
                    showlegend=True,
                )
            )

        fig.update_layout(
            title="Schedule Gantt Chart",
            xaxis_title=f"Time ({self._time_unit})",
            yaxis_title="Resource",
            barmode="overlay",
            showlegend=True,
            yaxis=dict(
                categoryorder="array",
                categoryarray=sorted(resources),
            ),
        )

        return self._apply_theme(fig)

    def plot_resource_utilization(self) -> Any:
        """Plot resource utilization over time.

        Shows total work assigned to each resource.

        Returns:
            Plotly Figure showing utilization.
        """
        resources = list(set(task.resource for task in self.tasks))
        colors = self._get_colors()

        utilization: Dict[str, float] = {}

        for resource in resources:
            resource_tasks = [t for t in self.tasks if t.resource == resource]

            total_work = 0.0
            for t in resource_tasks:
                if isinstance(t.start, (int, float)):
                    total_work += float(t.end) - float(t.start)
                elif isinstance(t.start, datetime) and isinstance(t.end, datetime):
                    total_work += (t.end - t.start).total_seconds() / 3600

            utilization[resource] = total_work

        fig = go.Figure(
            go.Bar(
                x=list(utilization.keys()),
                y=list(utilization.values()),
                marker_color=colors[0],
                text=[f"{v:.1f}" for v in utilization.values()],
                textposition="auto",
            )
        )

        fig.update_layout(
            title="Resource Utilization",
            xaxis_title="Resource",
            yaxis_title=f"Total Work ({self._time_unit})",
        )

        return self._apply_theme(fig)

    def plot_timeline(self) -> Any:
        """Plot timeline view of all tasks.

        Alternative to Gantt that shows all tasks in a linear timeline.

        Returns:
            Plotly Figure.
        """
        if not self.tasks:
            fig = go.Figure()
            fig.add_annotation(text="No tasks", x=0.5, y=0.5, showarrow=False)
            return self._apply_theme(fig)

        colors = self._get_colors()

        # Sort tasks by start time
        sorted_tasks = sorted(
            self.tasks,
            key=lambda t: float(t.start) if isinstance(t.start, (int, float)) else 0,
        )

        fig = go.Figure()

        for i, task in enumerate(sorted_tasks):
            if isinstance(task.start, (int, float)):
                start = float(task.start)
                end = float(task.end)
            else:
                start = 0
                end = 1

            fig.add_trace(
                go.Scatter(
                    x=[start, end],
                    y=[i, i],
                    mode="lines+markers",
                    name=f"{task.name} ({task.resource})",
                    line=dict(width=10, color=colors[i % len(colors)]),
                    hovertemplate=(
                        f"<b>{task.name}</b><br>"
                        f"Resource: {task.resource}<br>"
                        f"Duration: {end - start:.1f}<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title="Task Timeline",
            xaxis_title=f"Time ({self._time_unit})",
            yaxis=dict(
                tickmode="array",
                tickvals=list(range(len(sorted_tasks))),
                ticktext=[f"{t.name}" for t in sorted_tasks],
            ),
        )

        return self._apply_theme(fig)


__all__ = ["LXScheduleGantt", "LXScheduleTask"]