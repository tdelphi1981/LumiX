# Diet Problem: Evolution of Optimization Modeling

This directory contains **four implementations** of the same diet optimization problem, representing **60 years of modeling evolution**:

1. **`diet_problem.lp`**: LINDO (1960s-1980s) - Basic LP format
2. **`diet_problem.lg`**: LINGO (1988) - Set-based proprietary
3. **`diet_problem.mod`**: AMPL (1985-present) - Algebraic modeling
4. **`basic_lp.py`**: LumiX (2020s) - Data-driven Python

## Problem Description

**Minimize** the cost of daily food while meeting nutritional requirements:
- **Foods**: 6 options (Oatmeal, Chicken, Eggs, Milk, Apple Pie, Pork)
- **Constraints**: Minimum 2000 calories, 50g protein, 800mg calcium
- **Objective**: Minimize total cost

## Evolution Timeline

```
1960s          1985           1988           2020s
  |              |              |              |
LINDO  ───────> AMPL  ───────> LINGO  ───────> LumiX
  |              |              |              |
  │              │              │              └─ Data-driven, Python, Type-safe
  │              │              └─ Sets, Proprietary, Data sections
  │              └─ Algebraic, Named constraints, Multi-solver
  └─ Direct LP notation, Manual variables
```

**Key Distinction**: AMPL (1985) introduced algebraic modeling with named constraints and multi-solver support, positioning itself between LINDO's simplicity and modern data-driven approaches.

## Four-Way Side-by-Side Comparison

### 1. Variable Definition

#### LINDO (1960s - Simplest)
```lindo
! Variables named explicitly in objective/constraints
! X_Oatmeal, X_Chicken, X_Eggs, X_Milk, X_ApplePie, X_Pork
! No variable declaration section - variables defined by usage
MIN
    0.30 X_Oatmeal +
    2.40 X_Chicken +
    0.50 X_Eggs +
    0.60 X_Milk +
    1.60 X_ApplePie +
    2.90 X_Pork
```
- ❌ No variable declaration - implicit from usage
- ❌ Must manually type variable names everywhere
- ❌ No structured data whatsoever
- ✅ Very simple, matches textbook notation

#### LINGO (1988 - Set-Based)
```lingo
SETS:
    FOODS / Oatmeal, Chicken, Eggs, Milk, 'Apple Pie', Pork /:
        Servings,  ! Must manually list each food
        Cost,
        Calories,
        Protein,
        Calcium;
ENDSETS
```
- ⚠️ Manual enumeration of foods
- ⚠️ Separate data sections
- ❌ No type information
- ✅ Better than LINDO (has structure)

#### AMPL (1985 - Algebraic)
```ampl
# Explicit variable declarations with bounds
var X_Oatmeal >= 0;
var X_Chicken >= 0;
var X_Eggs >= 0;
var X_Milk >= 0;
var X_ApplePie >= 0;
var X_Pork >= 0;
```
- ✅ Explicit declarations (clearer than LINDO)
- ✅ Bounds in declaration (var X >= 0)
- ⚠️ Still manual enumeration
- ⚠️ No type information
- ✅ Works with multiple free solvers

#### LumiX (2020s - Data-Driven)
```python
@dataclass
class Food:
    name: str
    cost_per_serving: float
    calories: float
    protein: float
    calcium: float

FOODS = [
    Food("Oatmeal", 0.30, 110, 4, 2),
    Food("Chicken", 2.40, 205, 32, 12),
    # ...
]

servings = (
    LXVariable[Food, float]("servings")
    .continuous()
    .bounds(lower=0)
    .indexed_by(lambda f: f.name)
    .from_data(FOODS)  # Automatic expansion!
)
```
- ✅ Type-safe dataclass definition
- ✅ All food data in one place
- ✅ Automatic variable expansion
- ✅ IDE autocomplete for attributes

---

### 2. Data Entry

#### LINDO
```lindo
! No data section - all coefficients inline in constraints
! Objective function:
MIN
    0.30 X_Oatmeal + 2.40 X_Chicken + 0.50 X_Eggs + ...

! Calories constraint (every coefficient written):
Calories:
    110 X_Oatmeal + 205 X_Chicken + 160 X_Eggs + ...

! Protein constraint (coefficients repeated):
Protein:
    4 X_Oatmeal + 32 X_Chicken + 13 X_Eggs + ...

! Calcium constraint (coefficients repeated again):
Calcium:
    2 X_Oatmeal + 12 X_Chicken + 60 X_Eggs + ...
```
- ❌ Most verbose - coefficients scattered everywhere
- ❌ Each food's data written 4 times (obj + 3 constraints)
- ❌ Extremely error-prone - easy to misalign
- ❌ No separation of data and structure

#### LINGO
```lingo
DATA:
    Cost = 0.30 2.40 0.50 0.60 1.60 2.90;
    Calories = 110 205 160 160 420 260;
    Protein = 4 32 13 8 4 14;
    Calcium = 2 12 60 285 22 10;
ENDDATA
```
- ❌ Data scattered across multiple arrays
- ❌ Easy to misalign (no structure)
- ❌ Hard to add new foods (edit 4+ places)

#### AMPL
```ampl
# Coefficients inline in objective and constraints
minimize TotalCost:
    0.30*X_Oatmeal + 2.40*X_Chicken + 0.50*X_Eggs + ...;

subject to MinCalories:
    110*X_Oatmeal + 205*X_Chicken + 160*X_Eggs + ...;

subject to MinProtein:
    4*X_Oatmeal + 32*X_Chicken + 13*X_Eggs + ...;

subject to MinCalcium:
    2*X_Oatmeal + 12*X_Chicken + 60*X_Eggs + ...;
```
- ⚠️ Like LINDO, coefficients inline
- ✅ But with named constraints (clearer)
- ⚠️ Can use separate .dat files for data (more advanced)
- ⚠️ Still repeated per constraint

#### LumiX
```python
FOODS = [
    Food("Oatmeal", 0.30, 110, 4, 2),
    Food("Chicken", 2.40, 205, 32, 12),
    Food("Eggs", 0.50, 160, 13, 60),
    # ...
]
```
- ✅ Structured data (each food = one line)
- ✅ Type-checked attributes
- ✅ Easy to add: `FOODS.append(Food(...))`
- ✅ Can load from database/CSV/API

---

### 3. Objective Function

#### LINGO
```lingo
MIN = @SUM(FOODS(I): Cost(I) * Servings(I));
```
- Manual summation syntax
- Index variable `I` required

#### LumiX
```python
cost_expr = LXLinearExpression().add_term(
    servings,
    coeff=lambda f: f.cost_per_serving
)
model.minimize(cost_expr)
```
- ✅ Automatic summation over variable family
- ✅ Lambda extracts coefficient from data
- ✅ Type-safe: `f` is `Food`, IDE knows attributes

---

### 4. Constraints

#### LINGO
```lingo
@SUM(FOODS(I): Calories(I) * Servings(I)) >= 2000;
@SUM(FOODS(I): Protein(I) * Servings(I)) >= 50;
@SUM(FOODS(I): Calcium(I) * Servings(I)) >= 800;
@FOR(FOODS(I): Servings(I) >= 0);
```
- Manual loops with `@SUM` and `@FOR`
- Must specify non-negativity explicitly

#### LumiX
```python
model.add_constraint(
    LXConstraint("min_calories")
    .expression(
        LXLinearExpression().add_term(servings, lambda f: f.calories)
    )
    .ge()
    .rhs(MIN_CALORIES)
)
# Similar for protein, calcium
```
- ✅ Fluent API (method chaining)
- ✅ Named constraints
- ✅ Bounds set on variable definition

---

### 5. Solution Access

#### LINGO
```lingo
! Solution displayed in LINGO's solution window
! Manual inspection required
! Limited programmatic access
```

#### LumiX
```python
solution = optimizer.solve(model)

# Access by index key
food_by_name = {f.name: f for f in FOODS}
for food_name, qty in solution.get_mapped(servings).items():
    food = food_by_name[food_name]
    print(f"{food.name}: {qty:.2f} servings")
    # Full access to food.cost_per_serving, food.calories, etc.
```
- ✅ Programmatic access to all solution data
- ✅ Type-safe lookups
- ✅ Easy to post-process (export, visualize, etc.)

---

## Feature Comparison Table

| Feature | LINDO (1960s) | AMPL (1985) | LINGO (1988) | LumiX (2020s) |
|---------|---------------|-------------|--------------|---------------|
| **Language** | LP format | Algebraic | Proprietary | Python |
| **Type Safety** | ❌ None | ❌ None | ❌ None | ✅ Full type hints |
| **IDE Support** | ❌ None | ⚠️ Basic | ⚠️ Limited | ✅ Full autocomplete |
| **Data Source** | Inline in model | .dat files possible | Hardcoded in model | Database/CSV/API/Code |
| **Data Structure** | Scattered | Inline or params | Parallel arrays | Structured classes |
| **Verbosity** | ❌ Highest | ⚠️ Medium | ⚠️ Medium | ✅ Concise |
| **Extensibility** | ❌ Edit 4+ places | ⚠️ Edit multiple | ⚠️ Edit multiple | ✅ Add one line |
| **Version Control** | ❌ Very difficult | ⚠️ Better with .dat | ⚠️ Data + model mixed | ✅ Separate data/model |
| **Learning Curve** | ✅ Simple (textbook) | ⚠️ Algebraic | ⚠️ New language | ⚠️ Python knowledge |
| **Scalability** | ❌ Terrible (100s) | ✅ Good (with sets) | ⚠️ OK (1000s) | ✅ Excellent (any size) |
| **Solver Support** | LINDO only | ✅ Many (GLPK, etc) | LINGO only | OR-Tools, Gurobi, CPLEX |
| **Cost** | 💲 Commercial | ⚠️ Free community ed | 💲 Commercial | ✅ Free & open-source |
| **Integration** | ❌ None | ⚠️ Limited (scripts) | ⚠️ Standalone | ✅ Python ecosystem |
| **Debugging** | ❌ None | ⚠️ Basic | ⚠️ Limited tools | ✅ Full Python debugging |
| **Error Messages** | ❌ Basic | ⚠️ OK | ⚠️ Cryptic | ✅ Clear & helpful |
| **Testing** | ❌ None | ⚠️ Manual | ⚠️ Manual | ✅ pytest, unittest |
| **Collaboration** | ⚠️ License + manual | ✅ Academic standard | ⚠️ License required | ✅ Open to all |
| **Documentation** | ⚠️ Basic manuals | ✅ Excellent | ⚠️ Vendor-specific | ✅ Python docs + API |
| **Era** | Teaching tool | Academic standard | Production (legacy) | Modern development |

---

## Code Statistics

### Lines of Code (excluding comments)

| Metric | LINDO | AMPL | LINGO | LumiX (Python) |
|--------|-------|------|-------|----------------|
| Variable definitions | 0 (implicit) | 6 lines | ~10 lines | ~12 lines (type-safe) |
| Data entry | 0 (inline) | 0 (inline) | ~15 lines | ~6 lines (structured) |
| Objective | 7 lines | 4 lines | 1 line | 5 lines (readable) |
| Constraints | 30 lines | 18 lines | 4 lines | ~30 lines (fluent) |
| Solution handling | N/A (GUI) | N/A (solver) | N/A (GUI) | ~30 lines (programmatic) |
| **Total** | ~37 lines | ~28 lines | ~30 lines | ~83 lines |
| **Coefficient appearances** | 24× (4× each) | 24× (4× each) | 6× (arrays) | 1× (dataclass) |

**Key Insight**: Line count doesn't tell the whole story!

- **LINDO**: Shortest but most repetitive - each coefficient appears 4 times
- **AMPL**: Similar to LINDO but with cleaner syntax (named constraints)
- **LINGO**: Compact model with structure - coefficients in separate arrays
- **LumiX**: More lines but each coefficient appears ONCE - maximum DRY principle

**Maintainability Example**: Change Oatmeal cost from $0.30 to $0.35:
- LINDO: Find and edit 1 line in objective function (manual search)
- AMPL: Find and edit 1 line in minimize (easier with named sections)
- LINGO: Find and edit 1 position in Cost array (must count position)
- LumiX: Edit 1 number in `Food("Oatmeal", 0.30, ...)` → `0.35` (IDE autocomplete!)

While LINDO/AMPL seem simple, LumiX's type-checked approach prevents errors!

---

## Real-World Scenarios

### Scenario 1: Add a New Food
**Task**: Add "Rice" with cost=$0.40, 200 cal, 4g protein, 10mg calcium

#### LINDO
```lindo
! Must edit 4 separate places:

! 1. In MIN objective (add one line):
MIN
    ... existing foods ...
    0.40 X_Rice

! 2. In Calories constraint (add one line):
Calories:
    ... existing foods ...
    200 X_Rice >= 2000

! 3. In Protein constraint (add one line):
Protein:
    ... existing foods ...
    4 X_Rice >= 50

! 4. In Calcium constraint (add one line):
Calcium:
    ... existing foods ...
    10 X_Rice >= 800
```
❌ **Extremely error-prone**: Must edit 4 places, easy to miss one!
❌ If you forget to add Rice to one constraint, NO ERROR - just wrong results!

#### LINGO
```lingo
! Must edit in 3+ places:
SETS:
    FOODS / Oatmeal, Chicken, Eggs, Milk, 'Apple Pie', Pork, Rice /:
        ! ...

DATA:
    Cost = 0.30 2.40 0.50 0.60 1.60 2.90 0.40;  ! Add 0.40
    Calories = 110 205 160 160 420 260 200;     ! Add 200
    Protein = 4 32 13 8 4 14 4;                 ! Add 4
    Calcium = 2 12 60 285 22 10 10;             ! Add 10
ENDDATA
```
❌ Error-prone: must edit 5 locations perfectly aligned

#### LumiX
```python
FOODS.append(Food("Rice", 0.40, 200, 4, 10))
```
✅ One line, type-checked, impossible to misalign

---

### Scenario 2: Load Data from Database
**Task**: Use production database instead of hardcoded data

#### LINGO
```lingo
! Not possible - must export to file, manually format, copy-paste
! Or use LINGO's limited database connectivity (complex setup)
```
❌ Requires export/import workflow

#### LumiX
```python
# SQLAlchemy example
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("postgresql://...")
with Session(engine) as session:
    foods = session.query(FoodModel).all()

servings = (
    LXVariable[FoodModel, float]("servings")
    .continuous()
    .from_model(FoodModel, session=session)
)
```
✅ Native Python ORM support

---

### Scenario 3: Parametric Studies
**Task**: Solve for different calorie requirements (1500, 2000, 2500)

#### LINGO
```lingo
! Must manually edit and re-solve 3 times:
@SUM(FOODS(I): Calories(I) * Servings(I)) >= 1500;  ! Edit
! Save results manually
@SUM(FOODS(I): Calories(I) * Servings(I)) >= 2000;  ! Edit again
! Save results manually
@SUM(FOODS(I): Calories(I) * Servings(I)) >= 2500;  ! Edit again
```
❌ Manual, repetitive, error-prone

#### LumiX
```python
results = {}
for min_cal in [1500, 2000, 2500]:
    model, servings = build_diet_model(min_calories=min_cal)
    solution = optimizer.solve(model)
    results[min_cal] = solution.objective_value

# Plot results
import matplotlib.pyplot as plt
plt.plot(results.keys(), results.values())
```
✅ Programmatic, automated, can visualize

---

## When to Use Each

### Use LINGO when:
- You already have LINGO licenses
- Small, one-off problems
- Team familiar with LINGO syntax
- No need for integration with other systems

### Use LumiX when:
- Need type safety and IDE support
- Data comes from databases/APIs
- Frequent model changes
- Integration with Python ecosystem (pandas, numpy, etc.)
- Version control and collaboration important
- Teaching/learning optimization
- Open-source requirements
- Need to automate parametric studies

---

## Migration Path: LINGO → LumiX

1. **Extract data**: Convert LINGO DATA sections to Python dataclasses
2. **Convert sets**: Map LINGO sets to Python lists of instances
3. **Translate constraints**: Convert `@SUM` to `LXLinearExpression().add_term()`
4. **Update objective**: Use `.minimize()` or `.maximize()`
5. **Add solution handling**: Use `solution.get_mapped()` for results

**Example**: The diet problem migration took ~30 minutes, resulting in:
- Better maintainability
- Type safety
- IDE support
- No license costs

---

## Historical Perspective: 60 Years of Evolution

### LINDO Era (1960s-1980s): The Beginning
- **Philosophy**: Direct translation of mathematical LP notation
- **Strength**: Simple, matches textbook problems exactly
- **Weakness**: Doesn't scale, repetitive, error-prone
- **Use Case**: Teaching fundamentals, small problems (< 20 variables)

### AMPL Era (1985-present): Algebraic Modeling
- **Philosophy**: Separate model from data, support multiple solvers
- **Strength**: Clean syntax, named constraints, works with free solvers
- **Weakness**: Still standalone, limited IDE support
- **Use Case**: Academic research, prototyping, multi-solver comparison
- **Innovation**: Introduced the concept of solver-independent modeling

### LINGO Era (1988-2000s): Proprietary Structured Modeling
- **Philosophy**: Sets, loops, and integrated data sections
- **Strength**: More compact than AMPL, handles medium problems
- **Weakness**: Proprietary, locked to LINGO solvers, expensive
- **Use Case**: Production systems (legacy), 20-1000 variables

### LumiX Era (2020s): Data-Driven Development
- **Philosophy**: Separation of data, logic, and solving with full programming integration
- **Strength**: Type-safe, scalable, Python ecosystem, open-source
- **Weakness**: Requires Python knowledge
- **Use Case**: Modern software development, any problem size
- **Innovation**: Brings software engineering best practices to optimization

## Conclusion

All four approaches solve the same optimization problem, but represent different eras and philosophies:

**LINDO** (1960s) = Teaching tool, simple but verbose, textbook notation
**AMPL** (1985) = Academic standard, algebraic, multi-solver, still widely used
**LINGO** (1988) = Production legacy, structured but proprietary and expensive
**LumiX** (2020s) = Modern development, data-driven, scalable, open-source

LumiX provides:
- ✅ **Better developer experience** (type safety, IDE support)
- ✅ **Easier maintenance** (structured data, version control)
- ✅ **Greater flexibility** (Python ecosystem integration)
- ✅ **Lower cost** (open-source, no licenses)
- ✅ **Easier collaboration** (Python = universal language)

### When to Use Each

**Use LINDO when:**
- Teaching LP fundamentals in a classroom
- Very small, one-off problems (< 10 variables)
- Need exact textbook LP notation
- Already have LINDO license (rare nowadays)

**Use AMPL when:**
- Academic research and education
- Need to compare multiple solvers
- Rapid prototyping of optimization models
- Working in operations research courses
- Want clean algebraic modeling without full programming
- Have AMPL community edition (free for small problems)

**Use LINGO when:**
- Maintaining legacy LINGO codebase
- Team already trained in LINGO (sunk cost)
- Medium-sized production systems (if already invested)
- Need LINGO-specific features
- *Note: For new projects, consider AMPL or LumiX instead*

**Use LumiX when:**
- Starting a new project (recommended)
- Need modern software development practices
- Want open-source, collaborative development
- Need database/API integration
- Team knows Python
- Want type safety and IDE support
- Any size problem (scales infinitely)
- Integration with data science workflows

### The Evolution of Optimization Modeling

The progression **LINDO → AMPL → LINGO → LumiX** shows how optimization modeling has evolved:

1. **LINDO (1960s)**: Manual, textbook notation - pioneered computer-aided optimization
2. **AMPL (1985)**: Algebraic abstraction - separated model from solver
3. **LINGO (1988)**: Integrated structure - added sets and data sections
4. **LumiX (2020s)**: Data-driven integration - brought software engineering best practices

**For Modern Development**: While AMPL remains the academic standard and LINGO exists in legacy systems, **LumiX represents the future**: combining 60 years of optimization knowledge with modern software engineering practices (type safety, version control, testing, CI/CD, etc.).
