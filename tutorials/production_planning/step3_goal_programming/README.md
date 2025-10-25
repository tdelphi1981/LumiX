# Step 3: Goal Programming with Customer Orders (SQLAlchemy ORM)

## Overview

This is the third step in the Manufacturing Production Planning tutorial. It extends Step 2 by adding **customer orders as soft constraints** using LumiX's **goal programming** feature with **SQLAlchemy ORM integration**.

Customers can place orders with target quantities, and the optimization tries to satisfy these orders based on customer tier priority (Gold > Silver > Bronze), all while using type-safe ORM operations.

## What's New in Step 3

### Key Additions

1. **Customer Tiers**: Customers classified as Gold, Silver, or Bronze (ORM models)
2. **Customer Orders**: Production targets as soft constraints (goals) stored in database
3. **Priority Levels**: Orders prioritized based on customer tier
4. **Goal Programming**: Mix hard constraints (capacity) with soft goals (orders)
5. **Satisfaction Analysis**: Track which orders were fulfilled
6. **True ORM Pattern**: Database queried directly on-demand without pre-loading into Python lists

### Why Use Goal Programming?

In real-world production, **not all objectives are equally important**:

- **Hard constraints**: MUST be satisfied (e.g., capacity limits, material availability)
- **Soft constraints (goals)**: SHOULD be satisfied, but can be violated if necessary (e.g., customer orders)

**Goal programming** allows us to:
- Express customer orders as soft constraints
- Prioritize orders by customer importance
- Find the "best compromise" solution
- Track which orders were satisfied

### Why Use True ORM Pattern?

**Benefits of querying database directly (no pre-loading into lists):**
- **Memory Efficient**: No intermediate Python lists consuming memory
- **Database as Source of Truth**: Single source of truth, no data duplication
- **Type Safety**: Customer.tier gives IDE autocomplete, catches typos at dev time
- **Foreign Keys**: Automatic validation of customer_id and product_id
- **Cleaner Code**: No manual SQL string construction or list management
- **Easier Maintenance**: Schema changes reflected in Python models
- **Query Power**: Filter, paginate, or limit queries as needed
- **Scalability**: Better for large datasets (can use LIMIT, OFFSET)

## Customer Tier System

### Tier Definitions

| Tier | Priority | Description | Example Customers |
|------|----------|-------------|-------------------|
| **GOLD** | 1 (highest) | Premium customers, large orders | Fortune 500 companies |
| **SILVER** | 2 (medium) | Regular customers | Regional organizations |
| **BRONZE** | 3 (lowest) | New/small customers | Startups, small businesses |

### Priority Calculation (ORM Helper)

```python
from database import calculate_priority_from_tier

priority = calculate_priority_from_tier("GOLD")  # Returns 1
priority = calculate_priority_from_tier("SILVER")  # Returns 2
priority = calculate_priority_from_tier("BRONZE")  # Returns 3
```

## Mathematical Formulation

### Decision Variables (same as Step 2)

```
production[p] ≥ 0  (continuous, units of product p to produce)
```

### Objective Function

```
Maximize: Total Profit - Weighted Goal Violations
```

The solver maximizes profit while minimizing violations of customer orders, with higher-priority violations penalized more heavily.

### Hard Constraints (unchanged from Step 2)

1. **Machine Capacity**: Total hours ≤ available hours
2. **Material Availability**: Total material used ≤ available quantity

These constraints MUST all be satisfied.

### Soft Constraints (Goals - new in Step 3)

For each customer order, create a goal constraint:

```
production[p] ≥ target_quantity
  (goal, can be violated)
  priority = customer_tier_priority
  weight = 1.0
```

**Interpretation**:
- If production[p] >= target_quantity: Goal satisfied, no penalty
- If production[p] < target_quantity: Goal violated, penalty based on shortfall × priority_weight

### Goal Programming Objective

```
Minimize: Σ (priority_weight[p] × goal_weight × deviation)
          for all customer order goals

Where:
- priority_weight[1] = 10^6 (Gold customer orders)
- priority_weight[2] = 10^5 (Silver customer orders)
- priority_weight[3] = 10^4 (Bronze customer orders)
- deviation = amount by which order is not fulfilled
```

This ensures higher-priority customer orders are satisfied first.

## Database Schema Extensions

### ORM Models (database.py)

Instead of writing SQL, we define declarative models:

**Customer Model (NEW in Step 3):**
```python
class Customer(Base):
    """Customer ORM model with tier-based priority."""
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    tier = Column(String, nullable=False)
    priority_level = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("tier IN ('GOLD', 'SILVER', 'BRONZE')"),
        CheckConstraint("priority_level BETWEEN 1 AND 3"),
    )
```

**CustomerOrder Model (NEW in Step 3):**
```python
class CustomerOrder(Base):
    """Customer Order ORM model for goal programming."""
    __tablename__ = 'customer_orders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    target_quantity = Column(Float, nullable=False)
    due_week = Column(Integer, nullable=False)
    priority = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 3"),
        CheckConstraint("due_week >= 1"),
    )
```

## Running the Example

### Step 1: Populate the Database

```bash
cd tutorials/production_planning/step3_goal_programming
python sample_data.py
```

This creates 5 customers (2 Gold, 2 Silver, 1 Bronze) with 9 total orders using ORM.

**Output:**
```
================================================================================
PRODUCTION PLANNING DATABASE SETUP - STEP 3 (GOAL PROGRAMMING with ORM)
================================================================================

Initializing database...
Clearing existing data...
  ✓ Data cleared

Inserting products...
  Chair: $45.0/unit
  Table: $120.0/unit
  Desk: $200.0/unit

[...]

Inserting customers with tier-based priorities...
  [GOLD] Premium Office Furniture Inc. → Priority 1
  [GOLD] Global Workspace Solutions → Priority 1
  [SILVER] Regional School District → Priority 2
  [SILVER] Mid-Size Corp → Priority 2
  [BRONZE] Small Business Startup → Priority 3

Inserting customer orders (soft constraints)...
  [P1] Premium Office Furniture Inc.: 15.0 Desks
  [P1] Premium Office Furniture Inc.: 20.0 Tables
  [P1] Global Workspace Solutions: 50.0 Chairs
  [...]

Priority Distribution:
  Priority 1 (GOLD):   4 orders → Highest priority
  Priority 2 (SILVER): 3 orders → Medium priority
  Priority 3 (BRONZE): 2 orders → Lowest priority
```

### Step 2: Run the Optimization

```bash
python production_goals.py
```

The program will:
1. Initialize database and create ORM session
2. Verify database is populated (count only, no loading)
3. Build hard constraints - query database directly in loops
4. Add soft goal constraints - query customer orders from database
5. Solve using goal programming
6. Display production plan - query database for display
7. Analyze which orders were satisfied - query database for analysis

## Expected Output

```
================================================================================
LumiX Tutorial: Manufacturing Production Planning - Step 3
================================================================================

This example demonstrates:
  ✓ Goal programming with customer orders (ORM-based)
  ✓ Priority-based optimization (customer tier determines priority)
  ✓ Mixed hard constraints + soft goals
  ✓ Order fulfillment analysis
  ✓ Type-safe ORM operations

Verifying database...
  Found 3 products
  Found 2 machines
  Found 3 materials
  Found 5 customers
  Found 9 customer orders

Building production model with goal programming (ORM)...
[... model building output ...]

Adding soft goal constraints (SHOULD satisfy)...
  [P1] GOLD: 15.0 Desks for Premium Office Furniture Inc.
  [P1] GOLD: 20.0 Tables for Premium Office Furniture Inc.
  [P1] GOLD: 50.0 Chairs for Global Workspace Solutions
  [P1] GOLD: 10.0 Desks for Global Workspace Solutions
  [P2] SILVER: 30.0 Chairs for Regional School District
  [P2] SILVER: 10.0 Tables for Regional School District
  [P2] SILVER: 5.0 Desks for Mid-Size Corp
  [P3] BRONZE: 15.0 Chairs for Small Business Startup
  [P3] BRONZE: 8.0 Tables for Small Business Startup

[... optimization results ...]

================================================================================
GOAL SATISFACTION ANALYSIS
================================================================================

Priority 1 (GOLD customers):
--------------------------------------------------------------------------------
  ✓ SATISFIED: Premium Office Furniture Inc.
    Order: 15.0 Desks
    Actual: 18.75 Desks

  ✓ SATISFIED: Premium Office Furniture Inc.
    Order: 20.0 Tables
    Actual: 25.00 Tables

  ✗ NOT SATISFIED: Global Workspace Solutions
    Order: 50.0 Chairs
    Actual: 10.00 Chairs
    Shortfall: 40.00 units

Priority 1 Summary: 2/4 orders satisfied

Priority 2 (SILVER customers):
[...]

Priority 3 (BRONZE customers):
[...]
```

## ORM Operations for Goal Programming

### Querying Customers and Orders (True ORM Pattern)

**Using ORM without pre-loading into lists:**
```python
from database import init_database, get_session, Customer, CustomerOrder

# Initialize database and session
engine = init_database("sqlite:///production.db")
session = get_session(engine)

# Query customers directly in loops (no pre-loading)
for customer in session.query(Customer).all():
    print(f"{customer.name} - {customer.tier}")

# Query orders directly in loops (no pre-loading)
for order in session.query(CustomerOrder).all():
    print(f"Order {order.id}: {order.target_quantity} units")

# Query specific customer's orders directly
for order in session.query(CustomerOrder).filter_by(customer_id=1).all():
    print(f"Order {order.id} for customer 1")

# Query Gold tier customers directly
for customer in session.query(Customer).filter_by(tier="GOLD").all():
    print(f"Gold customer: {customer.name}")
```

### Adding Customers and Orders

**Using ORM:**
```python
from database import Customer, CustomerOrder

# Create customer using ORM
customer = Customer(
    id=1,
    name="Acme Corp",
    tier="GOLD",
    priority_level=1
)
session.add(customer)
session.commit()

# Create order using ORM
order = CustomerOrder(
    customer_id=1,
    product_id=3,
    target_quantity=50.0,
    due_week=1,
    priority=1  # Inherited from customer tier
)
session.add(order)
session.commit()
```

### Querying Customer Orders with Joins

**Using ORM:**
```python
from database import Customer, CustomerOrder, Product

# Get all orders with customer and product details
results = session.query(
    Customer.name.label('customer'),
    Customer.tier,
    Product.name.label('product'),
    CustomerOrder.target_quantity,
    CustomerOrder.priority
).join(
    Customer, CustomerOrder.customer_id == Customer.id
).join(
    Product, CustomerOrder.product_id == Product.id
).order_by(CustomerOrder.priority, Customer.name).all()

for row in results:
    print(f"[{row.tier}] {row.customer}: {row.target_quantity} {row.product}s")
```

## True ORM Pattern (Step 2 & Step 3)

This tutorial follows the **True ORM pattern** used in Step 2, where data is queried from the database on-demand without pre-loading into Python lists as function parameters.

### ✅ True ORM Pattern (CORRECT)

**What Step 2 and Step 3 do:**
```python
# Query database directly in loops - no pre-loading
def build_model(session):  # Only takes session, not lists
    # Query products on-demand
    for product in session.query(Product).all():
        production.add_index(product, ...)

    # Query machines on-demand
    for machine in session.query(Machine).all():
        # Query products again for constraint building
        for product in session.query(Product).all():
            hours = get_hours(product.id, machine.id)
            # ...
```

**When Dictionary Lookups Are Acceptable:**

In the True ORM pattern, creating **temporary dictionaries for lookups** within a function is acceptable to avoid N+1 query problems:

```python
# ✅ GOOD - Avoids N queries for N orders
products_dict = {p.id: p for p in session.query(Product).all()}  # 1 query
for order in session.query(CustomerOrder).all():  # 1 query
    product = products_dict.get(order.product_id)  # Dictionary lookup, not query
    # Use product...

# ❌ BAD - N queries for N orders
for order in session.query(CustomerOrder).all():  # 1 query
    product = session.query(Product).filter_by(id=order.product_id).first()  # N queries!
```

**Key Distinction:**
- ✅ Temporary dictionaries **within** functions for performance = OK
- ❌ Pre-loading lists and passing as **function parameters** = Violates True ORM

**Benefits:**
- Database is the single source of truth
- No pre-loaded function parameters
- More memory efficient
- Easier to add filters or limits to queries
- Consistent with Step 2's approach

### ❌ Hybrid/Anti-Pattern (AVOID)

**What to avoid (pre-loading into lists):**
```python
# DON'T DO THIS - pre-loading into lists
def build_model(session, products: List[Product], machines: List[Machine]):
    for product in products:  # Using pre-loaded list
        production.add_index(product, ...)

    for machine in machines:  # Using pre-loaded list
        for product in products:  # Using pre-loaded list
            hours = get_hours(product.id, machine.id)
            # ...

# Main function - DON'T DO THIS
products = session.query(Product).all()  # Pre-loading
machines = session.query(Machine).all()  # Pre-loading
build_model(session, products, machines)  # Passing lists
```

**Why this is worse:**
- Creates unnecessary intermediate lists
- Duplicates data (database + Python memory)
- Less flexible (can't filter queries easily)
- Inconsistent with Step 2's True ORM pattern

## Key LumiX Concepts

### 1. Marking Constraints as Goals

Convert a constraint to a goal with priority using ORM data:

```python
# Get customer info using lookup (from customers_dict)
customer = customers_dict.get(order.customer_id)

# Goal: production[product] ≥ target_quantity
# Use add_multi_term with lambda (same pattern as Step 2 demand constraints)
order_expr = LXLinearExpression().add_multi_term(
    production,
    coeff=lambda p, current_product=product: 1.0 if p.id == current_product.id else 0.0
)

model.add_constraint(
    LXConstraint(f"order_{order.id}_{customer.name.replace(' ', '_')}")
    .expression(order_expr)
    .ge()
    .rhs(order.target_quantity)
    .as_goal(priority=order.priority, weight=1.0)  # Mark as goal
)
```

### 2. Setting Goal Mode

Tell the model to use goal programming:

```python
model.set_goal_mode("weighted")  # Weighted sum approach
```

### 3. Preparing Goal Programming

Transform goals before solving (CRITICAL step):

```python
model.prepare_goal_programming()  # Must call before solving!
```

This automatically:
- Creates deviation variables (positive and negative)
- Relaxes goal constraints
- Builds the weighted objective function

### 4. Analyzing Goal Satisfaction (True ORM)

Check which orders were fulfilled using database queries and lookups:

```python
# Create lookups for efficient access (avoid N queries)
products_dict = {p.id: p for p in session.query(Product).all()}
customers_dict = {c.id: c for c in session.query(Customer).all()}

# Query orders directly from database
for order in session.query(CustomerOrder).all():
    product = products_dict.get(order.product_id)
    customer = customers_dict.get(order.customer_id)

    # Access solution using product.id (matches indexed_by)
    actual_production = solution.variables["production"][product.id]
    satisfied = actual_production >= order.target_quantity
    shortfall = max(0, order.target_quantity - actual_production)

    print(f"Customer: {customer.name} ({customer.tier})")
    print(f"  Order: {order.target_quantity} {product.name}s")
    print(f"  Actual: {actual_production:.2f}")
    if not satisfied:
        print(f"  Shortfall: {shortfall:.2f}")
```

## Implementation Patterns

### Pattern: Customer Order Goal with True ORM

```python
from database import Customer, CustomerOrder, Product

# Create lookups for efficient access (avoid N queries)
products_dict = {p.id: p for p in session.query(Product).all()}
customers_dict = {c.id: c for c in session.query(Customer).all()}

# Query customer orders directly from database (no pre-loading)
for order in session.query(CustomerOrder).all():
    # Find the product ORM object using lookup
    product = products_dict.get(order.product_id)

    # Get customer info using lookup
    customer = customers_dict.get(order.customer_id)

    # Goal: production[product] ≥ target_quantity
    # Use add_multi_term with lambda (same pattern as Step 2)
    order_expr = LXLinearExpression().add_multi_term(
        production,
        coeff=lambda p, current_product=product: 1.0 if p.id == current_product.id else 0.0
    )

    model.add_constraint(
        LXConstraint(f"order_{order.id}_{customer.name.replace(' ', '_')}")
        .expression(order_expr)
        .ge()
        .rhs(order.target_quantity)
        .as_goal(priority=order.priority, weight=1.0)
    )
```

### Pattern: Priority-Based Order Analysis (True ORM)

```python
# Create product lookup for efficient access
products_dict = {p.id: p for p in session.query(Product).all()}

# Group orders by priority - query directly from database
orders_by_priority = {}
for order in session.query(CustomerOrder).all():
    if order.priority not in orders_by_priority:
        orders_by_priority[order.priority] = []
    orders_by_priority[order.priority].append(order)

# Analyze each priority level
for priority in sorted(orders_by_priority.keys()):
    tier_name = "GOLD" if priority == 1 else "SILVER" if priority == 2 else "BRONZE"
    orders = orders_by_priority[priority]
    satisfied_count = 0

    for order in orders:
        # Query customer directly from database
        customer = session.query(Customer).filter_by(id=order.customer_id).first()
        product = products_dict.get(order.product_id)
        # ... check satisfaction ...
```

## Key Learnings

### 1. Goal Programming Workflow

The goal programming workflow in LumiX with True ORM pattern:

1. **Initialize DB**: `engine = init_database()`, `session = get_session(engine)`
2. **Verify data**: Use `.count()` to check database is populated (no loading)
3. **Build model** with hard constraints - query database directly in loops
4. **Add goals** using `.as_goal(priority, weight)` - query orders from database
5. **Set mode**: `model.set_goal_mode("weighted")`
6. **Prepare**: `model.prepare_goal_programming()` ← Don't forget!
7. **Solve**: `optimizer.solve(model)`
8. **Analyze**: Check which goals were satisfied by querying database directly

### 2. Priority Matters

Higher-priority goals dominate lower-priority goals:
- Priority 1 goals (Gold customers) are satisfied first
- Priority 2 goals (Silver) considered after P1 goals
- Priority 3 goals (Bronze) get lowest attention

The ORM models enforce valid priorities with check constraints.

### 3. Trade-offs Are Explicit

Goal programming makes trade-offs visible:
- Which orders were satisfied
- Which orders were violated
- By how much each order was missed

This transparency helps explain production decisions to customers.

### 4. Hard vs. Soft Constraints

Understanding the difference:

| Type | Description | Example | Violation |
|------|-------------|---------|-----------|
| **Hard** | Must be satisfied | Machine capacity | Infeasible |
| **Soft (Goal)** | Should be satisfied | Customer order | Penalized |

Goal programming lets you mix both types effectively.

### 5. ORM Benefits for Goal Programming

**Type Safety:**
```python
# ORM: IDE catches errors
order.target_quantity  # ✓ Autocomplete works
order.target_quntity   # ✗ IDE error: attribute doesn't exist

# Raw SQL: No error checking
row["target_quntity"]  # ✗ Runtime error only
```

**Foreign Key Validation:**
```python
# ORM automatically validates foreign keys
order = CustomerOrder(
    customer_id=999,  # ✗ Fails if customer doesn't exist
    product_id=1,
    target_quantity=50.0
)
session.add(order)
session.commit()  # IntegrityError: FOREIGN KEY constraint failed
```

## Troubleshooting

### All Goals Violated

**Possible Causes**:
- Orders collectively exceed capacity
- Not enough materials for all orders
- Conflicting order priorities

**Solution**:
- Review total order quantities vs. capacity using ORM aggregation
- Check material availability
- Some orders may need to be postponed

**ORM Query to Diagnose:**
```python
from sqlalchemy import func

# Total order quantity by product
totals = session.query(
    Product.name,
    func.sum(CustomerOrder.target_quantity).label('total_ordered')
).join(
    CustomerOrder, Product.id == CustomerOrder.product_id
).group_by(Product.name).all()

for product_name, total_ordered in totals:
    print(f"{product_name}: {total_ordered} units ordered")
```

### prepare_goal_programming() Forgotten

**Error**:
```
Warning: Model has goals but prepare_goal_programming() not called
```

**Solution**:
```python
model.set_goal_mode("weighted")
model.prepare_goal_programming()  # Don't forget!
solution = optimizer.solve(model)
```

### ORM Foreign Key Constraint Error

**Error**:
```
sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed
```

**Solution**: Ensure you insert entities in the correct order:
1. Customers, Products (no dependencies)
2. Customer Orders (depend on customers and products)

```python
# Correct order
session.add_all(customers)
session.commit()

session.add_all(products)
session.commit()

session.add_all(customer_orders)  # Now foreign keys are valid
session.commit()
```

## Goal Programming Modes: Weighted vs Sequential

LumiX supports two goal programming modes with fundamentally different behaviors:

### Mode Comparison

| Aspect | **WEIGHTED** | **SEQUENTIAL (Preemptive)** |
|--------|--------------|---------------------------|
| **Solving** | Single optimization solve | Multiple solves (one per priority) |
| **Objective** | Weighted sum of all priorities | Lexicographic optimization |
| **Trade-offs** | Allows trade-offs between priorities | NEVER compromises higher priorities |
| **Performance** | Faster (single solve) | Slower (multiple solves) |
| **Best For** | Soft preferences, relative importance | Strict hierarchy, non-negotiable priorities |

### Weighted Mode (Default in `production_goals.py`)

**How it works:**
```python
model.set_goal_mode("weighted")  # Single solve
model.prepare_goal_programming()
solution = optimizer.solve(model)
```

**Behavior:**
- Combines all priorities into a single objective function
- Uses exponential weights (e.g., 10^6 for P1, 10^4 for P2, 10^2 for P3)
- Allows trade-offs: May sacrifice 1 Priority 1 goal to satisfy 5 Priority 2 goals if the weights allow
- Computationally efficient - single optimization solve
- Best when priorities represent **relative importance** rather than strict requirements

**Example Result Pattern:**
```
Priority 1 (GOLD):   2/4 orders satisfied (50%)
Priority 2 (SILVER): 3/3 orders satisfied (100%)
Priority 3 (BRONZE): 2/2 orders satisfied (100%)
```
More balanced satisfaction across all priorities.

### Sequential Mode (Preemptive/Lexicographic)

**How it works:**
```python
model.set_goal_mode("sequential")  # Multiple solves
model.prepare_goal_programming()
solution = optimizer.solve(model)
```

**Behavior:**
- Solves Priority 1 first → fixes optimal P1 value as constraint
- Then solves Priority 2 (subject to maintaining P1 optimality)
- Then solves Priority 3 (subject to maintaining P1 and P2 optimality)
- **Never compromises** higher priorities for lower priorities
- Computationally expensive - multiple optimization solves
- Best when priorities are **strict requirements** (hierarchical)

**Example Result Pattern:**
```
Priority 1 (GOLD):   3/4 orders satisfied (75%)   ← Higher than weighted
Priority 2 (SILVER): 2/3 orders satisfied (67%)
Priority 3 (BRONZE): 0/2 orders satisfied (0%)    ← Lower than weighted
```
Strict priority enforcement - P1 optimized first.

### When to Use Each Mode

**Use WEIGHTED Mode When:**
- Priorities represent preferences rather than requirements
- You want balanced satisfaction across all priority levels
- Computational efficiency is important
- Trade-offs between priorities are acceptable
- Example: "Gold customers are more important, but not infinitely more important"

**Use SEQUENTIAL Mode When:**
- Higher priorities are non-negotiable requirements
- You need strict priority hierarchy enforcement
- "Priority 1 must be optimized first, Period 2 only with leftover resources"
- Computational time is not critical
- Example: "Gold customer orders MUST be prioritized, even if it means rejecting all Bronze orders"

### Comparing Both Modes

Run the comparison script to see behavioral differences:

```bash
python production_goals_comparison.py
```

**This script:**
- Solves the SAME model with both modes
- Shows side-by-side comparison of:
  - Goal satisfaction rates by priority
  - Production quantities
  - Total profit
  - Differences and trade-offs
- Explains why results differ

**Expected Observations:**
1. **Sequential mode** typically shows:
   - Higher Priority 1 satisfaction
   - Lower Priority 3 satisfaction
   - Strict priority enforcement

2. **Weighted mode** typically shows:
   - More balanced satisfaction across priorities
   - Possible trade-offs favoring multiple lower-priority goals

3. **When Priority 1 demands exceed capacity:**
   - Even sequential mode cannot satisfy all P1 goals
   - Hard constraints (capacity, materials) always enforced
   - Demonstrates realistic resource-constrained optimization

### Understanding GOLD Priority "Failure Rate"

In the current dataset, GOLD customers have **lower satisfaction rates** than SILVER/BRONZE customers. This is **correct optimization behavior**, not a bug:

**Why This Happens:**
1. **GOLD customers order premium products** (Desks) requiring 5.5 machine hours each
2. **Total GOLD demands exceed factory capacity** by 2-3× (physically impossible to fulfill all)
3. **Optimizer finds best feasible solution** given impossible demands
4. **BRONZE orders are resource-efficient** (Chairs/Tables) - easy to satisfy with leftover capacity

**Resource Analysis:**
```
GOLD Orders Alone Would Require:
  - Cutting: 105 hours (capacity: 80) → 131% over capacity
  - Assembly: 187.5 hours (capacity: 100) → 187% over capacity
  - Wood: 1,775 bf (available: 500) → 355% over capacity
  - Metal: 400 lbs (available: 200) → 200% over capacity

BRONZE Orders Only Require:
  - Cutting: 19.5 hours → 24% of capacity ✓
  - Assembly: 35 hours → 35% of capacity ✓
  - All materials well within limits ✓
```

**This demonstrates:**
- Hard constraints always enforced (no overproduction)
- Goal programming correctly handles infeasible soft constraints
- Resource-efficient orders naturally get satisfied when high-priority orders are impossible
- Realistic manufacturing scenario: cannot always satisfy all VIP customers

**To Improve GOLD Satisfaction:**
1. Increase factory capacity (more machines, materials)
2. Use sequential mode (prioritizes GOLD at expense of BRONZE)
3. Reduce GOLD order quantities
4. Multi-period planning (spread orders across weeks)

### Critical: Objective Value in Weighted Mode

**⚠️ IMPORTANT CAVEAT: `solution.objective_value` means different things in each mode!**

When using weighted goal programming, `solution.objective_value` does **NOT** return the actual profit. Instead, it returns a **transformed objective** that includes exponentially weighted goal deviation terms.

#### The Problem

**Weighted Mode Transformation:**
```python
# Original objective
objective = profit

# After model.set_goal_mode("weighted")
transformed_objective = profit + (10^6 × P1_deviations) + (10^4 × P2_deviations) + (10^2 × P3_deviations)

# solution.objective_value returns the TRANSFORMED value
print(solution.objective_value)  # $4,058,000 (includes huge weight terms!)
```

**Sequential Mode:**
```python
# Sequential mode returns actual profit from final solve iteration
print(solution.objective_value)  # $2,857.14 (real profit)
```

#### Why This Happens

LumiX's weighted goal programming converts the multi-objective problem into a single-objective problem by:

1. **Relaxing goal constraints** → Adding deviation variables (positive/negative)
2. **Assigning exponential weights** → Priority 1 = 10^6, Priority 2 = 10^4, Priority 3 = 10^2
3. **Combining into one objective** → `maximize: profit + Σ(weight × deviation_penalty)`

This ensures higher-priority goals dominate, but makes `solution.objective_value` **incomparable** between modes.

#### The Solution

**Always calculate actual profit manually:**

```python
def calculate_actual_profit(session, solution):
    """Calculate true profit from production quantities."""
    total_profit = 0.0
    for product in session.query(Product).all():
        quantity = solution.variables["production"][product.id]
        total_profit += quantity * product.profit_per_unit
    return total_profit

# Use this for comparison
actual_profit = calculate_actual_profit(session, solution)
print(f"Actual Profit: ${actual_profit:,.2f}")  # $2,822.00 (correct!)
```

#### Example: Why $4,058,000 is Wrong

**Production in weighted mode:**
- 50 Chairs × $45 = $2,250
- 2.86 Desks × $200 = $572
- **Actual profit: $2,822** ← This is the real value

**But solution.objective_value returns:**
```
$2,822 (profit) + $4,055,178 (weighted goal deviation terms) = $4,058,000
```

The huge number comes from exponential weights (10^6, 10^4, 10^2) multiplied by goal violations.

#### Best Practice

**For weighted mode:**
```python
# ❌ WRONG - Don't use this for profit comparison
profit = solution.objective_value  # Transformed objective!

# ✅ CORRECT - Calculate manually
profit = sum(solution.variables["production"][p.id] * p.profit_per_unit
             for p in session.query(Product).all())
```

**For sequential mode:**
```python
# ✅ OK - Sequential mode returns actual profit
profit = solution.objective_value  # This is correct in sequential mode
```

#### See the Comparison

Run `production_goals_comparison.py` to see:
- How both objective values are calculated
- Side-by-side comparison with actual profit
- Detailed explanation of the transformation

This script correctly calculates actual profit for both modes to ensure fair comparison.

## Next Steps

After completing Step 3, proceed to:

- **Step 4**: Large-scale multi-period planning with setup costs and inventory dynamics

## See Also

- **Step 2**: Database integration with SQLAlchemy ORM
- **Timetabling Step 3**: Similar goal programming with teacher preferences
- **LumiX Documentation**: Goal Programming guide
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/

---

**Tutorial Step 3 Complete!**

You've learned how to use goal programming for multi-objective optimization with customer orders using SQLAlchemy ORM for type-safe database operations. Now move on to Step 4 for large-scale multi-period planning with advanced features.
