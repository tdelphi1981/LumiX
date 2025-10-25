# Step 2: Database Integration with SQLAlchemy ORM

## Overview

This is the second step in the Manufacturing Production Planning tutorial. It extends Step 1 by integrating **SQLAlchemy ORM** for data storage and solution persistence.

The optimization model is identical to Step 1, but:
- **Direct ORM queries**: Data is queried from database on-demand, not pre-loaded into lists
- **No intermediate lists**: True ORM pattern - query only what's needed when it's needed
- **Solutions** are saved to the database for historical tracking
- **Type-safe operations** with IDE autocomplete support
- **Data management** is separated from optimization logic

## What's New in Step 2

### Key Changes from Step 1

1. **SQLAlchemy ORM**: Use declarative models instead of raw SQL queries
2. **Direct Database Queries**: Query data on-demand without pre-loading into lists
3. **True ORM Pattern**: No intermediate Python lists - database is the source of truth
4. **from_model() Integration**: LumiX queries database directly for variable creation
5. **Type Safety**: IDE autocomplete for model attributes
6. **Session Management**: Proper database transaction handling
7. **Solution Persistence**: Optimization results saved to database tables
8. **Cached Helpers**: Performance optimization with cached lookups for constraint coefficients
9. **Data Consistency**: Foreign key constraints ensure referential integrity

### Why Use SQLAlchemy ORM?

**Over Raw SQL:**
- **Type Safety**: Catch errors at development time, not runtime
- **IDE Support**: Autocomplete for model attributes and relationships
- **Less Boilerplate**: No manual SQL string construction
- **Easier Maintenance**: Schema changes reflected in Python code
- **Automatic Validation**: Foreign key enforcement built-in

**General Database Benefits:**
- **Persistence**: Data survives between program runs
- **Scalability**: Handle larger datasets efficiently
- **Multi-user**: Multiple users can access the same data
- **Integration**: Easy to connect with existing ERP/MRP systems
- **History**: Track multiple production plans over time
- **Querying**: Use ORM or SQL to analyze patterns and trends

## Database Schema

### ORM Models (database.py)

Instead of writing SQL, we define declarative models:

**Product Model:**
```python
class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    profit_per_unit = Column(Float, nullable=False)
    min_demand = Column(Float, nullable=False, default=0.0)
    max_demand = Column(Float, nullable=False)
```

**Machine Model:**
```python
class Machine(Base):
    __tablename__ = 'machines'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    available_hours = Column(Float, nullable=False)
```

**RawMaterial Model:**
```python
class RawMaterial(Base):
    __tablename__ = 'raw_materials'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    available_quantity = Column(Float, nullable=False)
    cost_per_unit = Column(Float, nullable=False)
```

### Relationship Models (Bill of Materials)

**ProductionRecipe Model** - Machine time requirements:
```python
class ProductionRecipe(Base):
    __tablename__ = 'production_recipes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    machine_id = Column(Integer, ForeignKey('machines.id'), nullable=False)
    hours_required = Column(Float, nullable=False)
```

**MaterialRequirement Model** - Material consumption:
```python
class MaterialRequirement(Base):
    __tablename__ = 'material_requirements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('raw_materials.id'), nullable=False)
    quantity_required = Column(Float, nullable=False)
```

### Solution Models

**ProductionSchedule Model** - Optimized production quantities:
```python
class ProductionSchedule(Base):
    __tablename__ = 'production_schedules'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    profit_contribution = Column(Float, nullable=False)
```

**ResourceUtilization Model** - Resource usage analysis:
```python
class ResourceUtilization(Base):
    __tablename__ = 'resource_utilization'

    id = Column(Integer, primary_key=True, autoincrement=True)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    resource_name = Column(String, nullable=False)
    used = Column(Float, nullable=False)
    available = Column(Float, nullable=False)
    utilization_pct = Column(Float, nullable=False)
```

## Files in This Example

- **`database.py`**: SQLAlchemy ORM models and database operations
- **`sample_data.py`**: Script to populate database with sample data using ORM
- **`production_db.py`**: Main optimization model using ORM session
- **`.gitignore`**: Exclude database files from version control
- **`README.md`**: This documentation file
- **`production.db`**: SQLite database (created at runtime, not in git)

## Running the Example

### Step 1: Populate the Database

First, create and populate the database with sample data:

```bash
cd tutorials/production_planning/step2_database_integration
python sample_data.py
```

**Output:**
```
================================================================================
PRODUCTION PLANNING DATABASE SETUP - STEP 2 (ORM)
================================================================================

Initializing database...
Clearing existing data...
  ✓ Data cleared

Inserting products...
  Chair: Profit $45.0/unit, Demand 10.0-100.0 units
  Table: Profit $120.0/unit, Demand 5.0-50.0 units
  Desk: Profit $200.0/unit, Demand 3.0-30.0 units

Inserting machines...
  Cutting Machine: 80.0 hours/week
  Assembly Station: 100.0 hours/week

Inserting raw materials...
  Wood (board feet): 500.0 units @ $5.0/unit
  Metal (pounds): 200.0 units @ $8.0/unit
  Fabric (yards): 150.0 units @ $12.0/unit

[...]

================================================================================
Database populated successfully!
================================================================================
  Products:              3
  Machines:              2
  Raw Materials:         3
  Production Recipes:    6
  Material Requirements: 8
================================================================================

Next step: Run 'python production_db.py' to solve the optimization
```

### Step 2: Run the Optimization

Now run the production planning optimization:

```bash
python production_db.py
```

The program will:
1. Initialize database and create ORM session
2. Load data from database using ORM queries
3. Build the optimization model with cached helpers
4. Solve the production planning problem
5. Display production plan and resource utilization
6. Save the solution back to database using ORM

## Expected Output

Same optimization results as Step 1, but with ORM integration:

```
================================================================================
LumiX Tutorial: Manufacturing Production Planning - Step 2
================================================================================

This example demonstrates:
  ✓ SQLAlchemy ORM declarative models
  ✓ LumiX's from_model(session) for direct database querying
  ✓ Type-safe ORM operations with IDE support
  ✓ Saving solutions using ORM session
  ✓ Performance optimization with cached helpers

Verifying database...
  Loaded 3 products
  Loaded 2 machines
  Loaded 3 materials

Building production planning model with ORM integration...
[... same optimization output as Step 1 ...]

Saving solution to database using ORM...
  Saved 3 production schedule entries
  Saved 2 machine utilization records
  Saved 3 material utilization records

================================================================================
Tutorial Step 2 Complete!
================================================================================

What changed from Step 1:
  → SQLAlchemy ORM models instead of Python lists
  → from_model(session) instead of from_data()
  → LumiX queries database directly
  → Type-safe ORM operations

ORM Benefits:
  ✓ No manual SQL queries
  ✓ IDE autocomplete for model attributes
  ✓ Automatic foreign key validation
  ✓ Type-safe database operations

Next Steps:
  → Step 3: Add customer orders with goal programming
```

## ORM Operations

### Database Initialization

Initialize database and create all tables from ORM models:

```python
from database import init_database, get_session

# Initialize database (creates all tables)
engine = init_database("sqlite:///production.db")

# Create session for database operations
session = get_session(engine)
```

### Inserting Data

**Using ORM (Type-Safe):**
```python
from database import Product, Machine

# Create ORM objects
product = Product(
    id=1,
    name="Chair",
    profit_per_unit=45.0,
    min_demand=10.0,
    max_demand=100.0
)

machine = Machine(
    id=1,
    name="Cutting Machine",
    available_hours=80.0
)

# Add to session and commit
session.add(product)
session.add(machine)
session.commit()

# Or add multiple at once
session.add_all([product, machine])
session.commit()
```

### Querying Data

**Using ORM Queries:**
```python
# Get all products
products = session.query(Product).all()

# Get all machines
machines = session.query(Machine).all()

# Filter by condition
chair = session.query(Product).filter_by(name="Chair").first()

# Get by ID
product = session.query(Product).filter_by(id=1).first()
```

### Solution Storage

**Saving Solutions with ORM:**
```python
from database import ProductionSchedule, ResourceUtilization

# Clear previous solutions
session.query(ProductionSchedule).delete()
session.query(ResourceUtilization).delete()

# Create new schedule entries
schedules = []
for product in products:
    quantity = solution.variables["production"][product]
    schedule = ProductionSchedule(
        product_id=product.id,
        quantity=quantity,
        profit_contribution=quantity * product.profit_per_unit
    )
    schedules.append(schedule)

# Add all and commit
session.add_all(schedules)
session.commit()
```

### Helper Functions

**Cached Lookups for Performance:**
```python
from database import (
    create_cached_machine_hours_checker,
    create_cached_material_requirement_checker
)

# Create cached checkers (queries DB once, caches results)
get_hours = create_cached_machine_hours_checker(session)
get_material = create_cached_material_requirement_checker(session)

# Fast cached lookups (no DB query per call)
hours = get_hours(product_id=1, machine_id=2)
material_qty = get_material(product_id=2, material_id=1)
```

**Benefits of Caching:**
- Reduces database queries from O(n) to O(1)
- Queries all data once upfront
- Returns closure with cached dictionary
- Significant performance improvement for constraint generation

### Session Management

**Proper Cleanup:**
```python
engine = init_database()
session = get_session(engine)

try:
    # Do database operations
    products = session.query(Product).all()
    # ... build and solve model ...
    session.commit()
finally:
    # Always close session
    session.close()
```

## Integration with LumiX

### Pattern: True ORM-Based Optimization with from_model()

This example demonstrates the **true ORM pattern** using SQLAlchemy: query data directly from the database on-demand, without pre-loading into lists, and use LumiX's `from_model()` for direct database integration.

```python
from lumix import LXVariable, LXLinearExpression, LXConstraint, LXModel
from database import (
    init_database,
    get_session,
    Product,
    Machine,
    RawMaterial,
    create_cached_machine_hours_checker,
)

# 1. Initialize database and session
engine = init_database("sqlite:///production.db")
session = get_session(engine)

try:
    # 2. Create cached helpers for performance (queries database once upfront)
    get_hours = create_cached_machine_hours_checker(session)

    # 3. Build LumiX variables using from_model() - LumiX queries database directly
    production = (
        LXVariable[Product, float]("production")
        .continuous()
        .bounds(lower=0)
        .indexed_by(lambda p: p.id)
        .from_model(Product, session)
    )

    # 4. Build constraints by querying database directly (no pre-loading)
    model = LXModel("production_planning_orm")
    model.add_variable(production)

    # Query machines on-demand for constraint building (no pre-loaded list)
    for machine in session.query(Machine).all():  # Direct query, no list
        expr = LXLinearExpression().add_multi_term(
            production,
            coeff=lambda p, m=machine: get_hours(p.id, m.id)  # Cached lookup
        )

        model.add_constraint(
            LXConstraint(f"machine_{machine.id}")
            .expression(expr)
            .le()
            .rhs(machine.available_hours)  # Access ORM attributes
        )

    # 5. Solve
    solution = optimizer.solve(model)

    # 6. Save results by querying database directly (no pre-loaded lists)
    save_solution_to_database(session, solution)  # Queries products/machines/materials inside

finally:
    session.close()
```

**Key Difference from Hybrid Approach:**
- **True ORM (this tutorial)**: Query data in loops (`for machine in session.query(Machine).all()`)
- **Hybrid/Anti-pattern**: Pre-load all data (`machines = session.query(Machine).all()`, then `for machine in machines`)
- **from_model() advantage**: LumiX queries database directly during variable creation

**Why True ORM is Better:**
- Less memory usage (no intermediate lists)
- Database is the single source of truth
- More flexible (can filter queries with `.filter_by()`)
- Better for large datasets (supports pagination/limits)
- Cleaner code (fewer temporary variables)

### Understanding from_model() Syntax

LumiX supports two patterns for `from_model()` depending on variable dimensionality:

**Single-Dimensional Variables** (this tutorial):
```python
# Variable indexed by one dimension: production[product]
production = (
    LXVariable[Product, float]("production")
    .indexed_by(lambda p: p.id)
    .from_model(Product, session)  # Pass Model class and session
)
```

**Multi-Dimensional Variables** (e.g., Timetabling tutorial):
```python
from lumix import LXIndexDimension

# Variable indexed by multiple dimensions: assignment[lecture, timeslot, classroom]
assignment = (
    LXVariable[Tuple[Lecture, TimeSlot, Classroom], int]("assignment")
    .indexed_by_product(
        LXIndexDimension(Lecture, lambda lec: lec.id).from_model(session),
        LXIndexDimension(TimeSlot, lambda ts: ts.id).from_model(session),
        LXIndexDimension(Classroom, lambda room: room.id).from_model(session),
    )
)
```

**Key Differences:**
- Single dimension: Use `.indexed_by()` + `.from_model(Model, session)` on variable
- Multiple dimensions: Use `.indexed_by_product()` with `LXIndexDimension(...).from_model(session)` for each dimension

### Benefits of This Pattern

1. **Separation of Concerns**: Data management separate from optimization logic
2. **Direct Queries**: No intermediate Python lists - query on-demand
3. **Type Safety**: IDE autocomplete for ORM model attributes (e.g., `product.proft_per_unit` → error)
4. **from_model() Integration**: LumiX can query database directly for variable creation
5. **Automatic Validation**: Foreign keys enforced by database
6. **Cached Performance**: Avoid redundant queries during model building
7. **Testability**: Easy to mock ORM session for testing
8. **Maintainability**: Schema changes reflected in Python code

## ORM Query Examples

You can query the database using SQLAlchemy ORM or raw SQL:

### View Production Recipes with Details (ORM)

```python
from database import Product, Machine, ProductionRecipe

results = session.query(
    Product.name.label('product'),
    Machine.name.label('machine'),
    ProductionRecipe.hours_required
).join(
    Product, ProductionRecipe.product_id == Product.id
).join(
    Machine, ProductionRecipe.machine_id == Machine.id
).order_by(Product.name, Machine.name).all()

for row in results:
    print(f"{row.product} on {row.machine}: {row.hours_required} hours")
```

### View Material Requirements (ORM)

```python
from database import Product, RawMaterial, MaterialRequirement

results = session.query(
    Product.name.label('product'),
    RawMaterial.name.label('material'),
    MaterialRequirement.quantity_required
).join(
    Product, MaterialRequirement.product_id == Product.id
).join(
    RawMaterial, MaterialRequirement.material_id == RawMaterial.id
).order_by(Product.name, RawMaterial.name).all()
```

### View Latest Production Schedule (ORM)

```python
from database import Product, ProductionSchedule

schedules = session.query(
    Product.name,
    ProductionSchedule.quantity,
    ProductionSchedule.profit_contribution
).join(
    Product, ProductionSchedule.product_id == Product.id
).order_by(Product.name).all()

for schedule in schedules:
    print(f"{schedule.name}: {schedule.quantity} units, ${schedule.profit_contribution}")
```

## Key Learnings

### 1. ORM as Data Source

LumiX works seamlessly with SQLAlchemy ORM objects. The ORM models serve as both database schema and Python dataclasses.

### 2. Type Safety Benefits

```python
# ORM: IDE catches errors
product.profit_per_unit  # ✓ Autocomplete works
product.proft_per_unit   # ✗ IDE error: attribute doesn't exist

# Raw SQL: No error checking
row["proft_per_unit"]    # ✗ Runtime error only
```

### 3. Performance with Caching

**Without caching:**
```python
# Called 1000 times during constraint generation
for product in products:
    for machine in machines:
        hours = session.query(...).filter_by(...).first()  # 1000 DB queries!
```

**With caching:**
```python
# Query once, cache results
get_hours = create_cached_machine_hours_checker(session)  # 1 DB query

# Fast lookups
for product in products:
    for machine in machines:
        hours = get_hours(product.id, machine.id)  # Dictionary lookup
```

### 4. Session Management

Always use try/finally to ensure sessions are closed:
```python
session = get_session(engine)
try:
    # Do work
    pass
finally:
    session.close()  # Ensures cleanup even if exception occurs
```

## Common Patterns

### Pattern 1: Initialize, Load, Solve, Save

```python
from database import init_database, get_session, clear_all_data

engine = init_database("sqlite:///production.db")
session = get_session(engine)

try:
    # Load
    products = session.query(Product).all()
    machines = session.query(Machine).all()

    # Solve
    model = build_model(session, products, machines, materials)
    solution = optimizer.solve(model)

    # Save
    save_solution(session, solution, products)
    session.commit()

finally:
    session.close()
```

### Pattern 2: Cached Helpers for Performance

```python
# Create cached checkers once
get_hours = create_cached_machine_hours_checker(session)
get_material = create_cached_material_requirement_checker(session)

# Use throughout model building (fast lookups)
hours = get_hours(product.id, machine.id)
qty = get_material(product.id, material.id)
```

### Pattern 3: Bulk Operations

```python
# Bulk insert (efficient)
schedules = [ProductionSchedule(...) for product in products]
session.add_all(schedules)
session.commit()

# Bulk delete
session.query(ProductionSchedule).delete()
session.commit()
```

## Troubleshooting

### Database Not Found Error

```
sqlalchemy.exc.OperationalError: no such table: products
```

**Solution:** Run `python sample_data.py` first to create and populate the database.

### Empty Database

```
❌ Database is empty! Please run sample_data.py first
```

**Solution:** The database exists but has no data. Run `python sample_data.py`.

### Foreign Key Constraint Error

```
sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed
```

**Solution:** Ensure you insert entities in the correct order:
1. Products, Machines, Materials (no dependencies)
2. Production Recipes, Material Requirements (depend on above)
3. Production Schedules (depend on products)

### Attribute Error

```
AttributeError: 'Product' object has no attribute 'proft_per_unit'
```

**Solution:** Typo in attribute name. Use IDE autocomplete to avoid this. Correct: `profit_per_unit`

## Next Steps

After completing Step 2, proceed to:

- **Step 3**: Add customer orders and goal programming with priorities
- **Step 4**: Large-scale multi-period planning with setup costs

## See Also

- **Step 1**: Basic production planning with Python lists
- **Timetabling Step 2**: Similar ORM integration pattern for scheduling problems
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/

---

**Tutorial Step 2 Complete!**

You've learned how to integrate LumiX with SQLAlchemy ORM for type-safe, efficient database operations. Now move on to Step 3 to add customer orders using goal programming.
