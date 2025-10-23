"""Meaningful logging utilities for LumiX.

This module provides enhanced logging capabilities specifically designed for optimization
models in LumiX. It offers specialized logging methods for tracking model construction,
solving progress, and solution analysis.

The LXModelLogger class extends Python's standard logging with domain-specific methods
for logging optimization-related events like variable creation, constraint addition,
solve status, and sensitivity analysis.

Key Features:
    - **Optimization-Specific Logging**: Methods tailored for model building and solving
    - **Automatic Timing**: Built-in solve time tracking
    - **Formatted Output**: Consistent, readable log messages for optimization events
    - **Configurable Levels**: Standard logging levels (DEBUG, INFO, WARNING, ERROR)

Examples:
    Basic usage for model logging::

        from lumix.utils import LXModelLogger

        logger = LXModelLogger(name="production_model", level=logging.INFO)

        # Log model creation
        logger.log_model_creation("ProductionPlan", num_vars=100, num_constraints=50)

        # Log solving
        logger.log_solve_start("Gurobi")
        # ... solve model ...
        logger.log_solve_end("Optimal", objective_value=12500.50)

    Debug-level logging for detailed tracking::

        logger = LXModelLogger(name="debug_model", level=logging.DEBUG)

        # Track each variable and constraint
        logger.log_variable_creation("production", "continuous", count=50)
        logger.log_constraint_creation("capacity", "<=", count=10)

See Also:
    - :class:`~lumix.core.model.LXModel`: Model builder class
    - Python's logging module: https://docs.python.org/3/library/logging.html
"""

import logging
from datetime import datetime
from typing import Any, Optional


class LXModelLogger:
    """Enhanced logging for optimization models.

    Provides specialized logging methods for tracking optimization model construction,
    solving progress, and solution analysis. Automatically handles timing and formatting
    for optimization-specific events.

    Attributes:
        logger (logging.Logger): Underlying Python logger instance
        start_time (Optional[datetime]): Timestamp when solve started (for timing)

    Examples:
        Create and use a model logger::

            from lumix.utils import LXModelLogger
            import logging

            logger = LXModelLogger(name="my_model", level=logging.INFO)
            logger.log_model_creation("ProductionModel", 100, 50)
            logger.log_solve_start("Gurobi")
            # ... solving happens ...
            logger.log_solve_end("Optimal", objective_value=42500.0)

    Note:
        The logger automatically creates a console handler if none exists. Multiple
        instances with the same name will share the same underlying Python logger.
    """

    def __init__(self, name: str = "lumix", level: int = logging.INFO):
        """Initialize model logger with specified name and logging level.

        Args:
            name: Logger name for identification. Defaults to "lumix". Use different
                names to distinguish between multiple models.
            level: Logging level from Python's logging module. Defaults to logging.INFO.
                Common values: logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR.

        Examples:
            Create logger with default settings::

                logger = LXModelLogger()

            Create logger with custom name and debug level::

                logger = LXModelLogger(name="my_model", level=logging.DEBUG)
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
        """Log the creation of an optimization model.

        Args:
            name: Name of the model being created
            num_vars: Total number of decision variables in the model
            num_constraints: Total number of constraints in the model

        Examples:
            Log model creation after building::

                logger.log_model_creation("ProductionPlan", num_vars=150, num_constraints=75)
                # Output: Created model 'ProductionPlan' with 150 variables and 75 constraints
        """
        self.logger.info(f"Created model '{name}' with {num_vars} variables and {num_constraints} constraints")

    def log_variable_creation(self, var_name: str, var_type: str, count: int = 1) -> None:
        """Log the creation of decision variables.

        Args:
            var_name: Name or identifier of the variable family
            var_type: Type of variable ("continuous", "integer", "binary")
            count: Number of variables created in this family. Defaults to 1.

        Examples:
            Log single variable creation::

                logger.log_variable_creation("profit", "continuous")

            Log variable family creation::

                logger.log_variable_creation("production", "continuous", count=50)
                # Output: Created 50 continuous variable(s): production
        """
        self.logger.debug(f"Created {count} {var_type} variable(s): {var_name}")

    def log_constraint_creation(self, constraint_name: str, sense: str, count: int = 1) -> None:
        """Log the creation of constraints.

        Args:
            constraint_name: Name or identifier of the constraint family
            sense: Constraint sense ("<=", ">=", "==")
            count: Number of constraints created in this family. Defaults to 1.

        Examples:
            Log single constraint::

                logger.log_constraint_creation("budget", "<=")

            Log constraint family::

                logger.log_constraint_creation("capacity", "<=", count=20)
                # Output: Created 20 constraint(s): capacity (<=)
        """
        self.logger.debug(f"Created {count} constraint(s): {constraint_name} ({sense})")

    def log_solve_start(self, solver_name: str) -> None:
        """Log the start of model solving and begin timing.

        Records the current timestamp for automatic solve time calculation.

        Args:
            solver_name: Name of the solver being used ("Gurobi", "CPLEX", "OR-Tools", etc.)

        Examples:
            Start solve logging::

                logger.log_solve_start("Gurobi")
                # Output: Starting solve with Gurobi...
        """
        self.start_time = datetime.now()
        self.logger.info(f"Starting solve with {solver_name}...")

    def log_solve_end(
        self,
        status: str,
        objective_value: Optional[float] = None,
        solve_time: Optional[float] = None,
    ) -> None:
        """Log the completion of model solving with results.

        Automatically calculates elapsed time if log_solve_start was called. Otherwise,
        uses the provided solve_time parameter.

        Args:
            status: Solve status ("Optimal", "Infeasible", "Unbounded", "TimeLimit", etc.)
            objective_value: Optimal objective value if available. Defaults to None.
            solve_time: Explicit solve time in seconds. Used if start time was not recorded.
                Defaults to None.

        Examples:
            Log successful solve with objective::

                logger.log_solve_end("Optimal", objective_value=42500.75)
                # Output: Solve completed: Optimal | Objective: 42500.7500 | Time: 2.35s

            Log solve without objective::

                logger.log_solve_end("Infeasible")
                # Output: Solve completed: Infeasible | Time: 0.15s
        """
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
        """Log a summary of the solution.

        Args:
            num_nonzero: Number of variables with non-zero values in the solution
            total_vars: Total number of variables in the model

        Examples:
            Log solution sparsity::

                logger.log_solution_summary(num_nonzero=25, total_vars=100)
                # Output: Solution has 25/100 non-zero variables
        """
        self.logger.info(f"Solution has {num_nonzero}/{total_vars} non-zero variables")

    def log_linearization(self, term_type: str, method: str, aux_vars: int) -> None:
        """Log automatic linearization applied to non-linear terms.

        Args:
            term_type: Type of non-linear term ("bilinear", "absolute", "min/max", etc.)
            method: Linearization method used ("McCormick", "big-M", "piecewise", etc.)
            aux_vars: Number of auxiliary variables added during linearization

        Examples:
            Log bilinear linearization::

                logger.log_linearization("bilinear", "McCormick", aux_vars=4)
                # Output: Linearized bilinear using McCormick (added 4 auxiliary variables)
        """
        self.logger.debug(f"Linearized {term_type} using {method} (added {aux_vars} auxiliary variables)")

    def log_scenario(self, scenario_name: str, modifications: int) -> None:
        """Log scenario analysis execution.

        Args:
            scenario_name: Name or identifier of the scenario being analyzed
            modifications: Number of parameter modifications in this scenario

        Examples:
            Log scenario run::

                logger.log_scenario("high_demand", modifications=5)
                # Output: Running scenario 'high_demand' with 5 modifications
        """
        self.logger.info(f"Running scenario '{scenario_name}' with {modifications} modifications")

    def log_sensitivity(self, var_name: str, reduced_cost: float) -> None:
        """Log sensitivity analysis results for a variable.

        Args:
            var_name: Name of the variable being analyzed
            reduced_cost: Reduced cost (shadow price) of the variable

        Examples:
            Log variable sensitivity::

                logger.log_sensitivity("production[Widget_A]", reduced_cost=-2.5)
                # Output: Sensitivity: production[Widget_A] reduced cost = -2.500000
        """
        self.logger.debug(f"Sensitivity: {var_name} reduced cost = {reduced_cost:.6f}")

    def info(self, message: str) -> None:
        """Log an informational message.

        Args:
            message: Message to log at INFO level

        Examples:
            Log custom info message::

                logger.info("Model preprocessing completed")
        """
        self.logger.info(message)

    def debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message: Message to log at DEBUG level

        Examples:
            Log debug details::

                logger.debug("Checking constraint matrix sparsity")
        """
        self.logger.debug(message)

    def warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: Message to log at WARNING level

        Examples:
            Log warning::

                logger.warning("Model contains unbounded variables")
        """
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: Message to log at ERROR level

        Examples:
            Log error::

                logger.error("Solver failed to find feasible solution")
        """
        self.logger.error(message)


__all__ = ["LXModelLogger"]
