"""Base visualizer class with common utilities.

This module provides the foundation for all LumiX visualization components,
including configuration management, export functionality, and common utilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from typing_extensions import Self

from ._compat import require_viz_dependencies, go
from .themes import LUMIX_COLORS, get_template

TModel = TypeVar("TModel")


@dataclass
class LXVisualizationConfig:
    """Configuration for visualization appearance.

    Controls the styling and behavior of all LumiX visualizations.

    Attributes:
        theme: Color theme name ('lumix', 'plotly', 'dark', 'light').
        width: Default figure width in pixels.
        height: Default figure height in pixels.
        title_font_size: Font size for titles.
        show_legend: Whether to show legend by default.
        interactive: Enable interactive features (hover, zoom).
        template: Plotly template name.
        color_sequence: Custom color sequence (overrides theme colors).

    Examples::

        config = LXVisualizationConfig(
            theme="dark",
            width=1200,
            height=800,
        )
    """

    theme: str = "lumix"
    width: int = 900
    height: int = 600
    title_font_size: int = 16
    show_legend: bool = True
    interactive: bool = True
    template: str = "plotly_white"
    color_sequence: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """Initialize color sequence if not provided."""
        if self.color_sequence is None:
            self.color_sequence = LUMIX_COLORS.copy()
        self.template = get_template(self.theme)


class LXBaseVisualizer(ABC, Generic[TModel]):
    """Abstract base class for all LumiX visualizers.

    Provides common functionality:

    - Configuration management
    - Export to HTML/PNG/SVG/PDF
    - Jupyter notebook display
    - Figure composition utilities

    Subclasses must implement the ``plot()`` method.

    Examples::

        class MyVisualizer(LXBaseVisualizer[MyModel]):
            def plot(self) -> Any:
                fig = go.Figure(...)
                return self._apply_theme(fig)
    """

    def __init__(self, config: Optional[LXVisualizationConfig] = None) -> None:
        """Initialize visualizer.

        Args:
            config: Visualization configuration. Uses defaults if not provided.
        """
        require_viz_dependencies()
        self.config = config or LXVisualizationConfig()
        self._figures: Dict[str, Any] = {}

    def configure(
        self,
        theme: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        **kwargs: Any,
    ) -> Self:
        """Configure visualization settings.

        Supports method chaining for fluent API.

        Args:
            theme: Color theme ('lumix', 'dark', 'light', etc.).
            width: Figure width in pixels.
            height: Figure height in pixels.
            **kwargs: Additional config options (title_font_size, show_legend, etc.).

        Returns:
            Self for method chaining.

        Examples::

            viz = (
                LXSolutionVisualizer(solution)
                .configure(theme="dark", width=1200)
            )
        """
        if theme is not None:
            self.config.theme = theme
            self.config.template = get_template(theme)
        if width is not None:
            self.config.width = width
        if height is not None:
            self.config.height = height
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self

    @abstractmethod
    def plot(self) -> Any:
        """Generate the main visualization figure.

        Returns:
            Plotly Figure object.
        """
        ...

    def show(self) -> None:
        """Display the visualization.

        Works in both Jupyter notebooks and opens a browser window
        for standalone Python scripts.

        Examples::

            viz = LXSolutionVisualizer(solution)
            viz.show()  # Opens interactive chart
        """
        fig = self.plot()
        fig.show()

    def to_html(
        self,
        path: Optional[Union[str, Path]] = None,
        full_html: bool = True,
        include_plotlyjs: Union[bool, str] = True,
    ) -> Optional[str]:
        """Export visualization to HTML.

        Args:
            path: File path to save HTML. If None, returns HTML string.
            full_html: Include full HTML document structure.
            include_plotlyjs: Include Plotly.js library.
                - True: Include full library
                - 'cdn': Use CDN link
                - False: Exclude (requires Plotly loaded elsewhere)

        Returns:
            HTML string if path is None, otherwise None.

        Examples::

            # Save to file
            viz.to_html("report.html")

            # Get HTML string
            html = viz.to_html()
        """
        fig = self.plot()
        html_content = fig.to_html(
            full_html=full_html,
            include_plotlyjs=include_plotlyjs,
        )

        if path is not None:
            Path(path).write_text(html_content)
            return None
        return html_content

    def to_image(
        self,
        path: Union[str, Path],
        format: str = "png",
        scale: float = 2.0,
    ) -> None:
        """Export visualization to static image.

        Requires kaleido package for image export.

        Args:
            path: Output file path.
            format: Image format ('png', 'svg', 'pdf', 'jpeg').
            scale: Resolution scale factor (2.0 = 2x resolution).

        Examples::

            viz.to_image("chart.png", scale=3.0)
            viz.to_image("chart.svg", format="svg")
        """
        fig = self.plot()
        fig.write_image(str(path), format=format, scale=scale)

    def _apply_theme(self, fig: Any) -> Any:
        """Apply configured theme to figure.

        Args:
            fig: Plotly Figure object.

        Returns:
            Figure with theme applied.
        """
        fig.update_layout(
            template=self.config.template,
            width=self.config.width,
            height=self.config.height,
            title_font_size=self.config.title_font_size,
            showlegend=self.config.show_legend,
        )
        return fig

    def _get_colors(self) -> List[str]:
        """Get color sequence for this visualizer.

        Returns:
            List of hex color strings.
        """
        return self.config.color_sequence or LUMIX_COLORS.copy()


__all__ = [
    "LXVisualizationConfig",
    "LXBaseVisualizer",
]