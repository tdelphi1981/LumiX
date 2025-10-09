"""Meaningful logging utilities for LumiX."""

import logging
from datetime import datetime
from typing import Any, Optional


class LXModelLogger:
    """Enhanced logging for optimization models."""

    def __init__(self, name: str = "lumix", level: int = logging.INFO):
        """
        Initialize model logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create console handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.start_time: Optional[datetime] = None

    def log_model_creation(self, name: str, num_vars: int, num_constraints: int) -> None:
        """Log model creation."""
        self.logger.info(f"Created model '{name}' with {num_vars} variables and {num_constraints} constraints")

    def log_variable_creation(self, var_name: str, var_type: str, count: int = 1) -> None:
        """Log variable creation."""
        self.logger.debug(f"Created {count} {var_type} variable(s): {var_name}")

    def log_constraint_creation(self, constraint_name: str, sense: str, count: int = 1) -> None:
        """Log constraint creation."""
        self.logger.debug(f"Created {count} constraint(s): {constraint_name} ({sense})")

    def log_solve_start(self, solver_name: str) -> None:
        """Log solve start."""
        self.start_time = datetime.now()
        self.logger.info(f"Starting solve with {solver_name}...")

    def log_solve_end(
        self,
        status: str,
        objective_value: Optional[float] = None,
        solve_time: Optional[float] = None,
    ) -> None:
        """Log solve completion."""
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
        else:
            elapsed = solve_time or 0.0

        if objective_value is not None:
            self.logger.info(
                f"Solve completed: {status} | Objective: {objective_value:.4f} | Time: {elapsed:.2f}s"
            )
        else:
            self.logger.info(f"Solve completed: {status} | Time: {elapsed:.2f}s")

    def log_solution_summary(self, num_nonzero: int, total_vars: int) -> None:
        """Log solution summary."""
        self.logger.info(f"Solution has {num_nonzero}/{total_vars} non-zero variables")

    def log_linearization(self, term_type: str, method: str, aux_vars: int) -> None:
        """Log linearization applied."""
        self.logger.debug(f"Linearized {term_type} using {method} (added {aux_vars} auxiliary variables)")

    def log_scenario(self, scenario_name: str, modifications: int) -> None:
        """Log scenario analysis."""
        self.logger.info(f"Running scenario '{scenario_name}' with {modifications} modifications")

    def log_sensitivity(self, var_name: str, reduced_cost: float) -> None:
        """Log sensitivity analysis."""
        self.logger.debug(f"Sensitivity: {var_name} reduced cost = {reduced_cost:.6f}")

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)


__all__ = ["LXModelLogger"]
