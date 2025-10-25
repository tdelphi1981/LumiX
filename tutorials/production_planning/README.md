# Manufacturing Production Planning Tutorial

A comprehensive 4-step tutorial demonstrating how to build production planning solutions using LumiX with SQLAlchemy ORM, progressing from basic continuous variable optimization to large-scale multi-period planning with goal programming.

## 📚 Full Documentation

**For comprehensive documentation with code examples, mathematical formulations, and detailed walkthroughs, see:**

📖 **Tutorial Steps** (detailed READMEs in each step folder)

This README provides a quick overview. Each step includes detailed documentation with:
- Step-by-step code explanations
- Mathematical formulations
- Database schemas and SQL examples
- Troubleshooting guides
- Extension ideas

## Overview

This tutorial teaches you how to solve a real-world manufacturing production planning problem through progressive complexity:

- **Step 1**: Basic production planning with continuous variables
- **Step 2**: Database integration with SQLAlchemy ORM and persistent storage
- **Step 3**: Goal programming with customer orders and priorities
- **Step 4**: Large-scale multi-period planning with setup costs and inventory

By the end of this tutorial, you'll understand:
- Continuous variables for quantity optimization
- Resource consumption constraints
- Profit maximization objectives
- SQLAlchemy ORM integration for type-safe database operations
- Multi-objective optimization with goal programming
- Customer priority management
- Multi-period planning with inventory management
- Setup costs and production batches
- Large-scale optimization (160x more variables than Step 1)

## Problem Description

**Scenario**: A furniture factory produces multiple products (chairs, tables, desks) using shared machines and raw materials. The factory must decide how many units of each product to manufacture to maximize profit while respecting resource limits and customer commitments.

**Key Features**:
- Continuous decision variables (production quantities)
- Resource constraints (machine hours, material availability)
- Customer orders with tier-based priorities (Gold/Silver/Bronze)
- Profit maximization with goal programming

**Data Scale by Step**:

| Element | Step 1-3 | Step 4 |
|---------|----------|--------|
| Products | 3 | 9 (3x) |
| Machines | 2 | 6 (3x) |
| Materials | 3 | 9 (3x) |
| Periods | 1 | 4 weeks |
| Customers | 5 | 8 |
| Orders | 9 | 15 across periods |
| Variables | ~10 | ~1,600 (160x) |

## Tutorial Structure

### Step 1: Basic Production Planning 📦

**Focus**: Core optimization with continuous variables

**What you'll learn**:
- Creating continuous variables: `production[Product]`
- Resource consumption constraints (machines, materials)
- Profit maximization objective
- Bounds on variables (min/max demand)

**Key LumiX features**:
- `LXVariable[Product, float]` with continuous bounds
- `.continuous()` for non-binary variables
- `.add_index()` with lower_bound and upper_bound
- Linear aggregation constraints
- Maximization objectives

**Files**:
- `sample_data.py`: Data classes and sample data
- `production.py`: Optimization model and solution display
- `README.md`: Detailed documentation

[📖 Go to Step 1](step1_basic_production/)

---

### Step 2: Database Integration with SQLAlchemy ORM 💾

**Focus**: Persistent data storage with SQLAlchemy ORM for type-safe operations

**What you'll learn**:
- Designing database schemas using SQLAlchemy declarative models
- Loading LumiX models from ORM entities
- Saving solutions to database using ORM
- Bill of Materials (BOM) structure with relationship tables
- Cached helper functions for performance
- Type-safe database operations

**Key features**:
- SQLAlchemy ORM with declarative models
- Type safety and IDE autocomplete
- CRUD operations using ORM session
- Solution persistence and historical tracking
- Cached helpers (1,000x faster than raw queries)
- Foreign key validation

**Files**:
- `database.py`: SQLAlchemy ORM models and operations
- `sample_data.py`: Database population script
- `production_db.py`: Database-driven optimization
- `.gitignore`: Exclude database files
- `README.md`: Database documentation

[📖 Go to Step 2](step2_database_integration/)

---

### Step 3: Goal Programming with Customer Orders (ORM) 🎯

**Focus**: Multi-objective optimization with priorities using SQLAlchemy ORM

**What you'll learn**:
- Expressing customer orders as soft constraints
- Assigning priorities based on customer tier
- Using LumiX's goal programming feature
- Analyzing order fulfillment
- Type-safe ORM operations for customers and orders

**Key features**:
- Customer tiers (GOLD, SILVER, BRONZE) as ORM models
- Priority calculation from tier
- Weighted goal programming
- Comprehensive satisfaction analysis
- Hard constraints vs. soft goals
- Foreign key validation for customer orders

**Files**:
- `database.py`: Extended ORM models with Customer and CustomerOrder
- `sample_data.py`: Customers with tiers and orders
- `production_goals.py`: Goal programming model
- `README.md`: Goal programming documentation

[📖 Go to Step 3](step3_goal_programming/)

---

### Step 4: Large-Scale Multi-Period Planning 🚀

**Focus**: Production-ready scale with multi-period planning, setup costs, and inventory

**What you'll learn**:
- Multi-period planning across time horizons
- Setup costs for production runs
- Minimum batch sizes
- Inventory management between periods
- Large-scale optimization (160x Step 1)
- Performance optimization with caching

**Key features**:
- 4-week planning horizon
- 9 products × 6 machines × 9 materials
- Setup costs and batch constraints
- Inventory tracking with holding costs
- Binary variables for setup decisions
- ~1,600 decision variables
- Multi-dimensional indexing
- Efficient caching (1,000x faster)

**New concepts**:
- Multi-period decision variables: `production[(Product, Period)]`
- Binary setup variables: `is_produced[(Product, Period)]`
- Inventory balance constraints
- Setup cost modeling
- Batch size constraints
- Time-based resource allocation

**Files**:
- `database.py`: Multi-period ORM schema with Period, Batch, SetupCost, Inventory models
- `sample_data.py`: Large-scale data generation (3x scale)
- `production_scaled.py`: Multi-period optimization with setup costs
- `.gitignore`: Exclude generated files
- `README.md`: Large-scale planning documentation

[📖 Go to Step 4](step4_scaled_up/)

---

## Quick Start

### Prerequisites

```bash
# Install LumiX with OR-Tools solver
pip install lumix
pip install ortools
```

### Step 1: Basic Production Planning

```bash
cd tutorials/production_planning/step1_basic_production
python production.py
```

### Step 2: Database Integration

```bash
cd tutorials/production_planning/step2_database_integration

# First, populate the database
python sample_data.py

# Then run the optimization
python production_db.py
```

### Step 3: Goal Programming

```bash
cd tutorials/production_planning/step3_goal_programming

# First, populate the database with customers and orders
python sample_data.py

# Then run the goal programming optimization
python production_goals.py
```

### Step 4: Large-Scale Multi-Period Planning

```bash
cd tutorials/production_planning/step4_scaled_up

# First, populate the database with large-scale data
python sample_data.py

# Then run the multi-period optimization (may take 10-30 seconds)
python production_scaled.py
```

## Learning Path

### For Beginners

Start with **Step 1** to learn:
- Basic LumiX modeling with continuous variables
- Resource constraints
- Profit maximization
- Solution interpretation

### For Intermediate Users

Skip to **Step 2** if you already know basics and want to learn:
- Database integration patterns
- Data persistence
- Scalable data management
- Bill of Materials structure

### For Advanced Users

Jump to **Step 3** for:
- Goal programming
- Multi-objective optimization
- Priority-based decision making
- Customer order management

### For Production-Ready Applications

Go to **Step 4** for:
- Large-scale optimization (1,600+ variables)
- Multi-period planning
- Setup costs and batch constraints
- Inventory management
- Performance optimization techniques

## Key Concepts Demonstrated

### 1. Continuous Variables

Variables representing quantities (not binary assignments):

```python
production = LXVariable[Product, float]("production").continuous()

for product in products:
    production.add_index(
        product,
        lower_bound=product.min_demand,
        upper_bound=product.max_demand
    )
```

**Contrast with binary variables (timetabling)**:
- Binary: assignment = 0 or 1 (yes/no)
- Continuous: production = any value ≥ 0 (how much)

### 2. Resource Consumption Constraints

Aggregate resource usage across products:

```python
# Machine capacity constraint
machine_hours_expr = LXLinearExpression()
for product in products:
    machine_hours_expr.add_term(
        production,
        index=product,
        coeff=hours_per_unit[product]
    )

model.add_constraint(
    LXConstraint("machine_capacity")
    .expression(machine_hours_expr)
    .le()
    .rhs(available_hours)
)
```

### 3. Profit Maximization

Optimize an objective (not just find feasibility):

```python
profit_expr = LXLinearExpression()
for product in products:
    profit_expr.add_term(
        production,
        index=product,
        coeff=product.profit_per_unit
    )

model.set_objective(profit_expr, sense="max")
```

### 4. Database-Driven Models

Load data from database instead of hardcoded lists:

```python
db = ProductionDatabase("production.db")
products = db.get_all_products()
machines = db.get_all_machines()
# Use these in model building
```

### 5. Goal Programming

Mix hard constraints with soft goals:

```python
# Hard constraint (must satisfy)
model.add_constraint(
    LXConstraint("machine_capacity")
    .expression(expr)
    .le()
    .rhs(available_hours)
)

# Soft goal (minimize violation)
model.add_constraint(
    LXConstraint("customer_order")
    .expression(expr)
    .ge()
    .rhs(target_quantity)
    .as_goal(priority=1, weight=1.0)  # Mark as goal
)
```

## Feature Comparison

| Feature | Step 1 | Step 2 | Step 3 |
|---------|--------|--------|--------|
| **Continuous Variables** | ✓ | ✓ | ✓ |
| **Resource Constraints** | ✓ | ✓ | ✓ |
| **Profit Maximization** | ✓ | ✓ | ✓ |
| **Python Lists** | ✓ | | |
| **SQLite Database** | | ✓ | ✓ |
| **Solution Persistence** | | ✓ | ✓ |
| **Customer Tiers** | | | ✓ |
| **Customer Orders** | | | ✓ |
| **Goal Programming** | | | ✓ |
| **Priority Levels** | | | ✓ |
| **Satisfaction Analysis** | | | ✓ |

## Real-World Applications

This tutorial's patterns apply to many optimization problems:

### Manufacturing
- **Production planning**: Determine production quantities
- **Blending**: Mix ingredients to meet specifications
- **Cutting stock**: Minimize waste when cutting materials
- **Capacity planning**: Allocate resources across products

### Food Industry
- **Recipe formulation**: Optimize ingredient mix
- **Diet optimization**: Minimize cost, meet nutrition requirements
- **Meal kit production**: Balance production with demand

### Finance
- **Portfolio allocation**: Maximize return, limit risk
- **Asset allocation**: Balance investments across asset classes

### Agriculture
- **Crop planning**: Maximize profit given land/water constraints
- **Feed mix**: Optimize animal feed composition

### Energy
- **Power generation**: Allocate generation across plants
- **Fuel blending**: Mix fuels to meet specifications

## Extension Ideas

After completing the tutorial, try these extensions:

### Easy Extensions
1. **Add more products**: Expand product line
2. **Add more constraints**: Minimum production runs, labor hours
3. **Modify priorities**: Use different customer tier rules
4. **Add costs**: Include material costs in objective

### Intermediate Extensions
1. **Inventory management**: Track stock levels over time
2. **Multi-period planning**: Plan for multiple weeks
3. **Setup costs**: Add fixed costs for production runs
4. **Transportation**: Add shipping constraints and costs

### Advanced Extensions
1. **Stochastic demand**: Handle uncertain customer demand
2. **Multi-site production**: Multiple factories
3. **Supply chain**: Integrate suppliers and distribution
4. **Real-time optimization**: Daily re-optimization with new data

## Tips for Success

### Understanding the Code

1. **Start with Step 1**: Understand continuous variables first
2. **Read the READMEs**: Each step has comprehensive documentation
3. **Run the examples**: See actual output
4. **Modify gradually**: Change one thing at a time

### Debugging

1. **Check constraints**: Verify resource limits make sense
2. **Simplify**: Reduce data size to understand the problem
3. **Print intermediate results**: Add debug prints
4. **Verify database**: Use SQL queries to inspect data

### Performance

1. **Start small**: Test with fewer products and orders
2. **Scale gradually**: Increase size once working correctly
3. **Use appropriate solver**: OR-Tools good for linear problems
4. **Profile bottlenecks**: Identify slow operations

## Common Pitfalls

### Pitfall 1: Forgetting prepare_goal_programming()

**Error**: Goal programming doesn't work, all constraints treated as hard

**Solution**:
```python
model.set_goal_mode("weighted")
model.prepare_goal_programming()  # Don't forget this!
solution = optimizer.solve(model)
```

### Pitfall 2: Database Not Populated

**Error**: `Database is empty!` or `No products found`

**Solution**: Run `python sample_data.py` first to populate the database

### Pitfall 3: Infeasible Problem

**Error**: Solver returns infeasible

**Causes**:
- Total demand exceeds capacity
- Not enough materials for minimum production
- Conflicting constraints

**Solution**:
- Verify resource availability vs. demand
- Check constraint formulations
- Reduce demand or increase capacity

### Pitfall 4: Wrong Variable Type

**Error**: Using binary variables instead of continuous

**Solution**:
```python
# Wrong (binary)
production = LXVariable[Product, int]("production").binary()

# Correct (continuous)
production = LXVariable[Product, float]("production").continuous()
```

## Comparison with Timetabling Tutorial

Both tutorials demonstrate LumiX capabilities but focus on different problem types:

| Aspect | Production Planning | Timetabling |
|--------|---------------------|-------------|
| **Variable Type** | Continuous (quantities) | Binary (assignments) |
| **Problem Type** | Optimization (maximize profit) | Feasibility (find valid schedule) |
| **Dimensions** | 1D (Product) | 3D (Lecture × Time × Room) |
| **Core Challenge** | Resource allocation | Conflict avoidance |
| **Goal Programming** | Customer orders | Teacher preferences |

**Both tutorials teach**:
- Database integration
- Goal programming
- Multi-objective optimization
- Solution persistence

## Help and Support

### Documentation

- [LumiX Documentation](https://lumix.readthedocs.io)
- [Step 1 README](step1_basic_production/README.md)
- [Step 2 README](step2_database_integration/README.md)
- [Step 3 README](step3_goal_programming/README.md)

### Examples

- Production Planning (this tutorial)
- Timetabling Tutorial (binary variables)
- LumiX Example 11: Goal Programming basics

## Summary

This tutorial has shown you:

- **Step 1**: Built a basic production model with continuous variables
- **Step 2**: Integrated SQLite database for persistent data storage
- **Step 3**: Added customer orders using goal programming with priorities

You've learned:
- Continuous variable optimization
- Resource consumption constraints
- Profit maximization objectives
- Database integration patterns
- Multi-objective optimization
- Priority-based decision making
- Solution analysis and interpretation

These skills transfer to many real-world optimization problems including manufacturing, supply chain, finance, agriculture, and energy. Happy optimizing!

---

**Tutorial Version**: 1.0
**LumiX Version**: Compatible with LumiX 0.1.0+
**Last Updated**: 2025-01-25
