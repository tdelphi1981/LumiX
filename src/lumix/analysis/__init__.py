"""
Analysis tools for LumiX optimization models.

This module provides comprehensive analysis capabilities for optimization models:

1. **Scenario Analysis** (`scenario`):
   - Create and run what-if scenarios
   - Compare different business conditions
   - Analyze parameter sensitivity

2. **Sensitivity Analysis** (`sensitivity`):
   - Analyze shadow prices (dual values)
   - Compute reduced costs
   - Identify binding constraints and bottlenecks

3. **What-If Analysis** (`whatif`):
   - Interactive parameter modification
   - Quick exploration of changes
   - Bottleneck identification

Examples:
    # Scenario Analysis
    from lumix.analysis import LXScenario, LXScenarioAnalyzer

    analyzer = LXScenarioAnalyzer(model, optimizer)
    analyzer.add_scenario(
        LXScenario("high_capacity")
        .modify_constraint_rhs("capacity", multiply=1.5)
    )
    results = analyzer.run_all_scenarios()
    print(analyzer.compare_scenarios())

    # Sensitivity Analysis
    from lumix.analysis import LXSensitivityAnalyzer

    sens_analyzer = LXSensitivityAnalyzer(model, solution)
    print(sens_analyzer.generate_report())

    bottlenecks = sens_analyzer.identify_bottlenecks()
    for name in bottlenecks:
        print(f"Bottleneck: {name}")

    # What-If Analysis
    from lumix.analysis import LXWhatIfAnalyzer

    whatif = LXWhatIfAnalyzer(model, optimizer)
    result = whatif.increase_constraint_rhs("capacity", by=100)
    print(f"Impact: ${result.delta_objective:,.2f}")

    bottlenecks = whatif.find_bottlenecks(top_n=5)
"""

from .scenario import LXScenario, LXScenarioAnalyzer, LXScenarioModification
from .sensitivity import (
    LXConstraintSensitivity,
    LXSensitivityAnalyzer,
    LXVariableSensitivity,
)
from .whatif import LXWhatIfAnalyzer, LXWhatIfChange, LXWhatIfResult

__all__ = [
    # Scenario Analysis
    "LXScenario",
    "LXScenarioAnalyzer",
    "LXScenarioModification",
    # Sensitivity Analysis
    "LXSensitivityAnalyzer",
    "LXVariableSensitivity",
    "LXConstraintSensitivity",
    # What-If Analysis
    "LXWhatIfAnalyzer",
    "LXWhatIfResult",
    "LXWhatIfChange",
]
