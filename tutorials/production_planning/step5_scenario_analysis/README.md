# Step 5: Multi-Scenario Analysis for Production Planning

## Overview

Step 5 demonstrates LumiX's capability for **scenario analysis and strategic decision-making** through optimization. This step builds on Step 4's multi-period planning by adding the ability to compare multiple what-if scenarios side-by-side.

**Business Value**: Instead of optimizing for a single set of assumptions, you can analyze how different market conditions, cost structures, or capacity constraints impact your production strategy. This supports data-driven strategic planning and risk assessment.

## What's New in Step 5

### 1. Scenario Management System

| Feature | Description |
|---------|-------------|
| 5 Scenarios | Baseline, High Demand, Supply Crisis, Expansion, Economic Downturn |
| Parameter Overrides | Demand, costs, capacity multipliers per scenario |
| Automated Solving | Solve all scenarios with a single command |
| Solution Tracking | Store and compare results across scenarios |

### 2. Interactive Multi-Scenario Report

**NEW Features**:
- **Scenario Selector Dropdown**: Switch between any of the 5 scenarios instantly
- **Comparison Dashboard Tab**: Side-by-side metrics, charts, and insights
- **Variance Analysis**: See profit impact vs baseline (+/- %)
- **Parameter Visualization**: Understand what changed in each scenario
- **Strategic Insights**: AI-generated recommendations per scenario

### 3. Five Demonstration Scenarios

#### Scenario 1: Baseline (Reference)
- Standard operating conditions from Step 4
- Normal demand, costs, capacity
- **Purpose**: Reference point for all comparisons

#### Scenario 2: High Demand (Optimistic)
- **Change**: +30% customer orders
- **Tests**: Can we meet growth demand?
- **Insights**: Bottlenecks under expansion

#### Scenario 3: Supply Chain Crisis
- **Changes**:
  - -40% material availability
  - +50% material costs
- **Tests**: Resilience to disruptions
- **Insights**: Which products are most vulnerable?

#### Scenario 4: Expansion
- **Changes**:
  - +50% machine capacity
  - -20% setup costs (economies of scale)
  - +20% demand
- **Tests**: ROI of capacity investment
- **Insights**: Optimal expansion strategy

#### Scenario 5: Economic Downturn
- **Changes**:
  - -30% customer orders
  - +10% holding costs
  - -20% profit margins
- **Tests**: Profitability in recession
- **Insights**: Cost reduction opportunities

## Database Schema Extensions

### New Tables (Step 5)

**scenarios**:
```sql
CREATE TABLE scenarios (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    scenario_type TEXT CHECK(scenario_type IN ('demand', 'cost', 'capacity', 'mixed')),
    is_baseline INTEGER CHECK(is_baseline IN (0, 1))
);
```

**scenario_parameters**:
```sql
CREATE TABLE scenario_parameters (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER REFERENCES scenarios(id),
    parameter_type TEXT NOT NULL,
    parameter_value REAL NOT NULL,
    parameter_description TEXT
);
```

**scenario_solutions**:
```sql
CREATE TABLE scenario_solutions (
    id INTEGER PRIMARY KEY,
    scenario_id INTEGER UNIQUE REFERENCES scenarios(id),
    solution_status TEXT NOT NULL,
    objective_value REAL NOT NULL,
    solve_time_seconds REAL NOT NULL,
    total_production_runs INTEGER NOT NULL,
    unique_products_made INTEGER NOT NULL,
    machine_utilization_pct REAL NOT NULL,
    material_utilization_pct REAL NOT NULL,
    orders_fulfilled INTEGER NOT NULL,
    orders_total INTEGER NOT NULL
);
```

### Extended Tables

**production_schedules_period** (added scenario_id):
```sql
ALTER TABLE production_schedules_period ADD COLUMN scenario_id INTEGER REFERENCES scenarios(id);
```

## Running the Example

### Step 1: Populate Database with Scenarios

```bash
cd tutorials/production_planning/step5_scenario_analysis
python sample_data.py
```

**Output**:
```
================================================================================
PRODUCTION PLANNING DATABASE SETUP - STEP 5 (SCENARIO ANALYSIS)
================================================================================

Features:
  • 5 Scenarios with parameter variations
  • 9 products × 6 machines × 9 materials × 4 periods
  • Mixed scenarios (demand, cost, capacity)

...

Scenarios:
  1. Baseline
  2. High Demand
     • 30% increase in all customer order quantities
  3. Supply Chain Crisis
     • 40% reduction in material availability per period
     • 50% increase in material costs
  4. Expansion
     • 50% increase in machine available hours
     • 20% reduction in setup costs (economies of scale)
     • 20% increase in customer order quantities
  5. Economic Downturn
     • 30% reduction in customer order quantities
     • 10% increase in inventory holding costs
     • 20% reduction in profit per unit (margin erosion)
```

### Step 2: Run Multi-Scenario Optimization

```bash
python production_scenarios.py
```

**What happens**:
1. Loads all 5 scenarios from database
2. For each scenario:
   - Applies parameter overrides
   - Builds optimization model
   - Solves with goal programming
   - Saves solution to database
3. Generates comprehensive HTML comparison report

**Expected runtime**: 60-120 seconds (5 scenarios × ~20 seconds each)

### Step 3: View the Interactive Report

```bash
open production_scenarios_report.html  # macOS
xdg-open production_scenarios_report.html  # Linux
start production_scenarios_report.html  # Windows
```

**Report Structure**:

**Tab 1: Scenario Comparison** (NEW!)
- **Comparison Matrix**: Key metrics across all 5 scenarios
- **Profit Comparison Chart**: Visual profit differences
- **Scenario Insights Cards**: Summary of each scenario's impact

**Tab 2: Summary Dashboard** (per scenario)
- Scenario selector dropdown at top
- All metrics from Step 4 for selected scenario
- Switches instantly when you select different scenario

## Key Concepts

### 1. Scenario Parameters

Define how each scenario differs from baseline:

```python
# Example: High Demand scenario
ScenarioParameter(
    scenario_id=2,
    parameter_type="demand_multiplier",
    parameter_value=1.3,  # 30% increase
    parameter_description="30% increase in all customer order quantities"
)
```

**Supported parameter types**:
- `demand_multiplier`: Scale customer order quantities
- `profit_margin_multiplier`: Adjust product profitability
- `holding_cost_multiplier`: Change inventory costs
- `machine_capacity_multiplier`: Modify machine hours
- `material_availability_multiplier`: Adjust material supply
- `material_cost_multiplier`: Change material prices
- `setup_cost_multiplier`: Modify fixed setup costs

### 2. Applying Scenario Overrides

Overrides are applied at model-building time:

```python
def apply_scenario_overrides(session, scenario_id):
    """Apply parameter multipliers to base data."""
    scenario_params = get_scenario_parameters(session, scenario_id)

    # Apply to products
    profit_mult = scenario_params.get("profit_margin_multiplier", 1.0)
    modified_profits = {
        p.id: p.profit_per_unit * profit_mult
        for p in products
    }

    # Apply to machines
    machine_mult = scenario_params.get("machine_capacity_multiplier", 1.0)
    modified_capacity = {
        m.id: m.available_hours * machine_mult
        for m in machines
    }

    # ... etc for all parameters
    return modified_data
```

### 3. Multi-Scenario Workflow

```python
# Pseudocode for production_scenarios.py
scenarios = session.query(Scenario).all()

all_solutions = {}
for scenario in scenarios:
    # 1. Get parameter overrides
    params = get_scenario_parameters(session, scenario.id)

    # 2. Apply to base data
    modified_data = apply_scenario_overrides(session, scenario.id)

    # 3. Build model with modified data
    model = build_scenario_model(session, scenario.id, modified_data)

    # 4. Solve
    solution = optimizer.solve(model)

    # 5. Save with scenario_id
    save_scenario_solution(session, scenario.id, solution)

    # 6. Store for comparison
    all_solutions[scenario.id] = solution

# 7. Generate comparison report
generate_multi_scenario_html_report(scenarios, all_solutions, ...)
```

### 4. Comparison Dashboard

The comparison dashboard provides:

**Quantitative Comparison**:
```
| Metric                  | Baseline  | High Demand | Supply Crisis | Expansion | Downturn  |
|-------------------------|-----------|-------------|---------------|-----------|-----------|
| Total Profit            | $45,280   | $58,150     | $22,340       | $67,890   | $31,450   |
|                         | (0%)      | (+28.4%)    | (-50.7%)      | (+50.0%)  | (-30.5%)  |
| Machine Utilization     | 68.5%     | 89.2%       | 45.3%         | 59.7%     | 47.8%     |
| Order Fulfillment Rate  | 86.7%     | 73.3%       | 60.0%         | 93.3%     | 100.0%    |
```

**Visual Comparison**:
- Bar charts comparing profits across scenarios
- Utilization gauges per scenario
- Fulfillment rate progress bars

**Strategic Insights**:
- Which scenario yields highest profit?
- Which resources become bottlenecks?
- Trade-offs between fulfillment and efficiency
- Risk assessment (worst-case scenario impact)

## Implementation Patterns

### Pattern 1: Creating Scenarios

```python
# In sample_data.py
def populate_scenarios(session):
    # Create scenario
    scenario = Scenario(
        id=2,
        name="High Demand",
        description="30% increase in customer orders...",
        scenario_type="demand",
        is_baseline=0
    )
    session.add(scenario)
    session.commit()

    # Add parameter overrides
    param = ScenarioParameter(
        scenario_id=2,
        parameter_type="demand_multiplier",
        parameter_value=1.3,
        parameter_description="30% increase in customer order quantities"
    )
    session.add(param)
    session.commit()
```

### Pattern 2: Building Scenario-Specific Models

```python
def build_scenario_model(session, scenario_id, scenario_name):
    # Apply overrides
    modified_data = apply_scenario_overrides(session, scenario_id)

    # Build model (same structure as Step 4)
    model = LXModel(f"scenario_{scenario_id}")
    production = LXVariable[...].continuous()
    # ... create variables ...

    # Objective with modified profits
    for product in products:
        profit = modified_data["product_profits"][product.id]  # Use override!
        obj_expr.add_term(production, coeff=profit)

    # Constraints with modified capacities
    for machine in machines:
        capacity = modified_data["machine_hours"][machine.id]  # Use override!
        model.add_constraint(
            LXConstraint(...).le().rhs(capacity)
        )

    return model, production, inventory
```

### Pattern 3: Saving Scenario Results

```python
def save_scenario_solution(session, scenario_id, solution):
    # Save production schedule with scenario_id
    for product, period in production_indices:
        qty = solution.variables["production"][(product.id, period.id)]
        schedule = ProductionSchedulePeriod(
            scenario_id=scenario_id,  # Link to scenario!
            product_id=product.id,
            period_id=period.id,
            quantity=qty
        )
        session.add(schedule)

    # Save high-level metrics
    scenario_solution = ScenarioSolution(
        scenario_id=scenario_id,
        objective_value=solution.objective_value,
        solve_time_seconds=solve_time,
        orders_fulfilled=count_fulfilled_orders(...)
    )
    session.add(scenario_solution)
    session.commit()
```

## Performance Considerations

### Scenario Count vs. Solve Time

| Scenarios | Total Solve Time | Avg per Scenario |
|-----------|------------------|------------------|
| 1         | ~20 seconds      | 20s              |
| 5         | ~100 seconds     | 20s              |
| 10        | ~200 seconds     | 20s              |

**Insight**: Scenarios solve independently, so you can run them in parallel if needed.

### Optimization for Many Scenarios

If running 10+ scenarios:

```python
# Option 1: Parallel solving (advanced)
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(solve_scenario, scenario_id)
        for scenario_id in scenario_ids
    ]
    results = [f.result() for f in futures]

# Option 2: Incremental solving
# Solve baseline first, use as warm start for similar scenarios
```

## Real-World Applications

### Manufacturing

**Question**: Should we invest in expanding capacity?

**Scenarios**:
1. Baseline (current capacity)
2. Small expansion (+25% capacity, -10% setup costs)
3. Large expansion (+50% capacity, -20% setup costs)
4. High demand + expansion
5. Recession + no expansion

**Decision**: Compare ROI, break-even demand, downside risk

### Supply Chain

**Question**: How vulnerable are we to material shortages?

**Scenarios**:
1. Baseline (normal supply)
2. Single supplier disruption (-30% key material)
3. Multi-supplier disruption (-50% all materials)
4. Price spike (+100% material costs)
5. Combined shortage + price spike

**Decision**: Identify critical materials, evaluate safety stock

### Strategic Planning

**Question**: What's our 3-year expansion roadmap?

**Scenarios**:
1. Year 1 baseline
2. Year 2: +20% demand, current capacity
3. Year 2: +20% demand, +30% capacity
4. Year 3: +50% demand, +50% capacity
5. Year 3: +50% demand, +100% capacity

**Decision**: Timing of capacity investments, expected profitability

## Comparison with Step 4

| Aspect | Step 4 | Step 5 |
|--------|--------|--------|
| **Scenarios** | 1 (implicit) | 5 (explicit) |
| **Parameter Variation** | Manual | Automated |
| **Comparison** | N/A | Built-in dashboard |
| **Strategic Value** | Single optimization | What-if analysis |
| **Database** | Single solution | Multi-scenario tracking |
| **Report** | Single view | Scenario selector + comparison |

## Troubleshooting

### Problem: Scenarios solve differently than expected

**Symptom**: Scenario results don't match manual calculation

**Diagnosis**:
```python
# Check applied parameters
params = get_scenario_parameters(session, scenario_id)
print(f"Demand multiplier: {params.get('demand_multiplier', 1.0)}")

# Verify modified data
modified_data = apply_scenario_overrides(session, scenario_id)
print(f"Modified machine hours: {modified_data['machine_hours']}")
```

**Solution**: Ensure parameter_type names match exactly in override logic

### Problem: Report shows wrong scenario

**Symptom**: Clicking scenario selector doesn't update view

**Diagnosis**: JavaScript scenario summaries not properly encoded

**Solution**: Check that all scenarios have saved solutions:
```python
for scenario in scenarios:
    solution = session.query(ScenarioSolution).filter_by(scenario_id=scenario.id).first()
    assert solution is not None, f"Missing solution for scenario {scenario.id}"
```

### Problem: Some scenarios infeasible

**Symptom**: Scenario 3 (Supply Crisis) returns "infeasible"

**Explanation**: This is expected! Severe parameter changes can make problems infeasible.

**Handling**:
```python
if solution.status == "infeasible":
    print(f"⚠️ Scenario {scenario.name} is infeasible")
    print(f"  Reason: Constraints too restrictive given parameters")
    # Still save partial results for comparison
    save_infeasible_scenario_info(...)
```

## Extension Ideas

### Easy Extensions

1. **Add More Scenarios**: Create 6th scenario (e.g., "Automation" with -50% labor costs)
2. **Custom Parameters**: Add new parameter types (e.g., `labor_cost_multiplier`)
3. **Scenario Grouping**: Categorize scenarios (optimistic/pessimistic/realistic)
4. **Export Comparison**: Generate CSV/Excel with scenario comparison table

### Intermediate Extensions

1. **Sensitivity Analysis**: Automatically generate scenarios by varying one parameter
2. **Monte Carlo Scenarios**: Random parameter sampling for risk analysis
3. **Scenario Templates**: Save/load scenario configurations
4. **Multi-Objective Scenarios**: Different objective functions per scenario

### Advanced Extensions

1. **Stochastic Programming**: Model uncertainty within a single scenario
2. **Robust Optimization**: Find solution that performs well across all scenarios
3. **Scenario Tree**: Sequential decision-making across time periods
4. **Real-Time Scenarios**: Re-solve daily with actual demand data

## Key Learnings

### 1. Scenario Analysis Power

**Before Step 5**: "Our optimal production plan is..."
**After Step 5**: "Under normal conditions, plan A is optimal. But if demand increases by 30%, we hit capacity constraints. If materials become scarce, we should prioritize high-margin products."

**Value**: Transforms single-point optimization into strategic decision support.

### 2. Parameter Sensitivity

Small parameter changes can have large impacts:
- 30% demand increase → +28% profit (sublinear due to capacity constraints)
- 40% material shortage → -51% profit (superlinear due to infeasibility)

**Insight**: Non-linear relationships reveal critical bottlenecks.

### 3. Trade-off Analysis

Expansion scenario shows:
- +50% capacity, +20% demand → +50% profit
- But requires capital investment
- Break-even if demand increase < 15%

**Decision**: Expansion justified only if confident in demand growth.

### 4. Risk Assessment

Worst-case scenario (Supply Chain Crisis):
- Profit drops to 49% of baseline
- Only 60% of orders fulfilled
- High-priority orders still met (risk mitigation)

**Strategy**: Build safety stock for critical materials, diversify suppliers.

## Next Steps

You've completed the Production Planning tutorial! You've learned:

✅ **Step 1**: Basic continuous variable optimization
✅ **Step 2**: Database integration with SQLAlchemy ORM
✅ **Step 3**: Goal programming with customer priorities
✅ **Step 4**: Large-scale multi-period planning
✅ **Step 5**: Multi-scenario analysis for strategic decisions

**Advanced Topics**:
- Stochastic optimization (demand uncertainty)
- Robust optimization (worst-case guarantees)
- Multi-stage planning (decision trees)
- Real-time re-optimization (rolling horizon)
- Integration with forecasting systems
- Automated scenario generation

## See Also

- **Timetabling Step 4**: Similar large-scale with binary variables
- **LumiX Documentation**: Scenario analysis guide
- **Example 11**: Goal programming basics
- **Research Papers**: Stochastic programming, robust optimization

---

**Tutorial Complete!**

You've mastered production planning optimization from basic to strategic scenario analysis using LumiX with SQLAlchemy ORM. These techniques apply to manufacturing, supply chain, finance, agriculture, and any domain requiring decision-making under uncertainty. Happy optimizing!
