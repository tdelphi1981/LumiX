# Scenario Analysis Example

## Overview

This example demonstrates LumiX's **scenario analysis** capabilities for exploring different business conditions and strategic decisions through what-if scenarios.

## Problem: Production Planning Under Uncertainty

A manufacturing company wants to understand how different business scenarios affect their optimal production plan and profitability:

- **Optimistic Scenario**: Market expansion with increased resource capacity
- **Pessimistic Scenario**: Resource constraints due to market conditions
- **Realistic Scenario**: Moderate growth with balanced expansion
- **Strategic Scenarios**: Labor investment, automation, material procurement

## Key Features Demonstrated

### 1. Scenario Creation (`LXScenario`)

```python
optimistic = (
    LXScenario[Product]("market_expansion")
    .modify_constraint_rhs("capacity_Labor Hours", multiply=1.30)
    .modify_constraint_rhs("capacity_Machine Hours", multiply=1.20)
    .describe("Market expansion: increase all resource capacities")
)
```

### 2. Batch Scenario Execution (`LXScenarioAnalyzer`)

```python
analyzer = LXScenarioAnalyzer(model, optimizer, include_baseline=True)
analyzer.add_scenarios(optimistic, pessimistic, realistic)
results = analyzer.run_all_scenarios()
```

### 3. Scenario Comparison

```python
print(analyzer.compare_scenarios())
best = analyzer.get_best_scenario(maximize=True)
```

### 4. Parameter Sensitivity Analysis

```python
labor_sensitivity = analyzer.sensitivity_to_parameter(
    "capacity_Labor Hours",
    values=[0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3],
    modification_type="rhs_multiply"
)
```

## Running the Example

```bash
cd examples/08_scenario_analysis
python scenario_analysis.py
```

## Expected Output

```
SCENARIO ANALYSIS: Production Planning Under Different Conditions
====================================================================

CREATING BUSINESS SCENARIOS
--------------------------------------------------------------------

1. OPTIMISTIC SCENARIO: Market Expansion
   - Hire more workers (+30% labor capacity)
   - Purchase new machines (+20% machine capacity)
   - Increase material procurement (+25% materials)

...

SCENARIO COMPARISON RESULTS
====================================================================
Baseline Objective: $12,345.67

Scenario                       Objective         Status    vs Baseline
--------------------------------------------------------------------------------
market_expansion               $15,234.89      optimal         +23.4%
moderate_growth                $13,456.78      optimal          +9.0%
labor_investment               $13,234.56      optimal          +7.2%
automation                     $12,987.65      optimal          +5.2%
baseline                       $12,345.67      optimal             -
resource_constraints           $10,123.45      optimal         -18.0%
material_procurement           $11,234.56      optimal          +2.5%
```

## Scenarios Included

### 1. **Market Expansion** (Optimistic)
- +30% labor capacity
- +20% machine capacity
- +25% raw materials
- **Use Case**: Planning for market growth

### 2. **Resource Constraints** (Pessimistic)
- -20% labor capacity
- -15% material availability
- **Use Case**: Risk assessment, contingency planning

### 3. **Moderate Growth** (Realistic)
- +10% all resources
- **Use Case**: Conservative growth planning

### 4. **Labor Investment**
- +50% labor capacity
- **Use Case**: Workforce expansion strategy

### 5. **Automation**
- +40% machine capacity
- -10% labor capacity
- **Use Case**: Technology investment evaluation

### 6. **Material Procurement**
- +30% raw material capacity through better supplier contracts
- **Use Case**: Supply chain optimization, reducing material bottlenecks

## Key Learnings

### 1. Strategic Planning
- Compare multiple business scenarios simultaneously
- Identify best and worst case outcomes
- Quantify risks and opportunities

### 2. Sensitivity Analysis
- Understand how profitability varies with capacity
- Identify which resources have highest impact
- Determine marginal value of capacity increases

### 3. Investment Prioritization
- Compare ROI of different capacity expansions
- Prioritize investments based on profit impact
- Balance risk and return

### 4. Risk Assessment
- Quantify downside risk of resource constraints
- Evaluate robustness of business plan
- Plan for contingencies

## Business Insights

The example generates actionable insights such as:

- **Resource Impact**: Labor capacity has the highest impact on profitability
- **Investment ROI**: Each 10% increase in labor yields X% profit gain
- **Risk Exposure**: Resource constraint scenario shows Y% downside risk
- **Best Strategy**: Market expansion shows highest profit potential

## Use Cases

1. **Strategic Planning**: Evaluate multi-year growth scenarios
2. **Investment Decisions**: Compare capital investment options
3. **Risk Management**: Assess impact of supply chain disruptions
4. **Market Analysis**: Model different market conditions
5. **Capacity Planning**: Optimize resource expansion strategies

## See Also

- **Sensitivity Analysis**: `examples/09_sensitivity_analysis/`
- **What-If Analysis**: `examples/10_whatif_analysis/`
- **Production Planning**: `examples/01_production_planning/`
