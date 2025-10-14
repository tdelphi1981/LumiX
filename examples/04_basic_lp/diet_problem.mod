# ========================================================================
# AMPL Model: Diet Problem
# ========================================================================
#
# Modern algebraic modeling language for comparison with LumiX
#
# Problem: Minimize cost of food while meeting nutritional requirements
#
# AMPL Characteristics:
# - Modern algebraic modeling language (1985, still widely used)
# - Works with open-source solvers (GLPK, CBC, HiGHS)
# - Named variables and constraints (better than LINDO)
# - Still algebraic/declarative (not imperative like Python)
# - Good middle ground between LINDO and LumiX
# - Widely used in academia and industry
# - Free AMPL Community Edition available
#
# Compare with:
# - LINDO: More verbose, older syntax
# - LINGO: Proprietary, set-based
# - LumiX: Data-driven Python, fully integrated
# ========================================================================

# ==================== VARIABLE DECLARATIONS ====================
# Decision variables: servings of each food
# All variables are non-negative (servings >= 0)

var X_Oatmeal >= 0;
var X_Chicken >= 0;
var X_Eggs >= 0;
var X_Milk >= 0;
var X_ApplePie >= 0;
var X_Pork >= 0;

# ==================== OBJECTIVE FUNCTION ====================
# Minimize total cost ($)
# Cost per serving: Oatmeal=$0.30, Chicken=$2.40, Eggs=$0.50,
#                   Milk=$0.60, ApplePie=$1.60, Pork=$2.90

minimize TotalCost:
    0.30*X_Oatmeal +
    2.40*X_Chicken +
    0.50*X_Eggs +
    0.60*X_Milk +
    1.60*X_ApplePie +
    2.90*X_Pork;

# ==================== CONSTRAINTS ====================

# Constraint 1: Minimum 2000 calories
# Calories per serving: Oatmeal=110, Chicken=205, Eggs=160,
#                       Milk=160, ApplePie=420, Pork=260
subject to MinCalories:
    110*X_Oatmeal +
    205*X_Chicken +
    160*X_Eggs +
    160*X_Milk +
    420*X_ApplePie +
    260*X_Pork >= 2000;

# Constraint 2: Minimum 50 grams protein
# Protein per serving (g): Oatmeal=4, Chicken=32, Eggs=13,
#                          Milk=8, ApplePie=4, Pork=14
subject to MinProtein:
    4*X_Oatmeal +
    32*X_Chicken +
    13*X_Eggs +
    8*X_Milk +
    4*X_ApplePie +
    14*X_Pork >= 50;

# Constraint 3: Minimum 800 mg calcium
# Calcium per serving (mg): Oatmeal=2, Chicken=12, Eggs=60,
#                           Milk=285, ApplePie=22, Pork=10
subject to MinCalcium:
    2*X_Oatmeal +
    12*X_Chicken +
    60*X_Eggs +
    285*X_Milk +
    22*X_ApplePie +
    10*X_Pork >= 800;

end;

# ========================================================================
# COMPARISON: AMPL vs LINDO vs LINGO vs LumiX
# ========================================================================
#
# 1. SYNTAX CLARITY:
#    LINDO:  Basic LP format, verbose
#    AMPL:   ✅ Cleaner, named constraints
#    LINGO:  Set-based, more abstract
#    LumiX:  Python, most readable
#
# 2. VARIABLE NAMING:
#    LINDO:  X_Oatmeal (implicit declaration)
#    AMPL:   var X_Oatmeal >= 0; (explicit, clear bounds)
#    LINGO:  Servings(I) (indexed by set)
#    LumiX:  servings[food] (indexed by data instances)
#
# 3. CONSTRAINT NAMING:
#    LINDO:  Labels only (Calories:)
#    AMPL:   ✅ subject to MinCalories: (explicit keyword)
#    LINGO:  Implicit in @SUM
#    LumiX:  LXConstraint("min_calories") (string name + object)
#
# 4. SOLVER COMPATIBILITY:
#    LINDO:  LINDO solvers only (commercial)
#    AMPL:   ✅ Many solvers (GLPK, CBC, HiGHS, Gurobi, CPLEX)
#    LINGO:  LINGO solvers only (commercial)
#    LumiX:  OR-Tools, Gurobi, CPLEX (extensible)
#
# 5. DATA MANAGEMENT:
#    LINDO:  ❌ Inline only, scattered
#    AMPL:   ⚠️ Can use .dat files (separate data)
#    LINGO:  ⚠️ DATA section in model
#    LumiX:  ✅ Python dataclasses, databases, APIs
#
# 6. SCALABILITY:
#    LINDO:  ❌ Terrible (manual expansion)
#    AMPL:   ⚠️ Better with sets (not shown here)
#    LINGO:  ⚠️ Good with sets
#    LumiX:  ✅ Excellent (automatic from data)
#
# 7. MODERN FEATURES:
#    LINDO:  ❌ None (1960s technology)
#    AMPL:   ⚠️ Some (can use scripts)
#    LINGO:  ⚠️ Limited
#    LumiX:  ✅ Full Python ecosystem
#
# 8. COST:
#    LINDO:  💲 Commercial license
#    AMPL:   ✅ Free community edition + free solvers
#    LINGO:  💲 Commercial license
#    LumiX:  ✅ Completely free & open-source
#
# 9. LEARNING CURVE:
#    LINDO:  ✅ Simple (but limited)
#    AMPL:   ⚠️ Moderate (algebraic modeling)
#    LINGO:  ⚠️ Moderate (proprietary syntax)
#    LumiX:  ⚠️ Moderate (need Python)
#
# 10. INTEGRATION:
#     LINDO:  ❌ Standalone
#     AMPL:   ⚠️ Limited (can call from scripts)
#     LINGO:  ⚠️ Limited
#     LumiX:  ✅ Full Python integration
#
# ========================================================================
# AMPL ADVANTAGES:
# ========================================================================
#
# Better than LINDO:
# - Named constraints (subject to MinCalories)
# - Explicit variable declarations with bounds
# - Works with modern free solvers
# - Cleaner, more structured syntax
#
# Better than LINGO:
# - Not proprietary (community edition free)
# - More solver options
# - Widely taught in universities
# - Better documentation
#
# Still not as good as LumiX for:
# - Data management (still inline coefficients)
# - Type safety (no IDE support)
# - Integration (standalone tool)
# - Scalability (manual variable naming)
# - Modern development practices
#
# ========================================================================
# ADVANCED AMPL FEATURES (not shown here):
# ========================================================================
#
# AMPL can be more sophisticated with sets and parameters:
#
# set FOODS;
# param cost {FOODS};
# param calories {FOODS};
# param protein {FOODS};
# param calcium {FOODS};
#
# var servings {FOODS} >= 0;
#
# minimize TotalCost: sum {f in FOODS} cost[f] * servings[f];
#
# subject to MinCalories: sum {f in FOODS} calories[f] * servings[f] >= 2000;
# ...
#
# Then use a separate .dat file:
#
# set FOODS := Oatmeal Chicken Eggs Milk ApplePie Pork;
# param cost := Oatmeal 0.30 Chicken 2.40 ... ;
# ...
#
# This is closer to LINGO's approach and much better than the simple
# version shown above. However, even advanced AMPL lacks:
# - Type safety (no compile-time checking)
# - IDE integration (limited autocomplete)
# - Database connectivity (requires external scripts)
# - Modern dev tools (testing, version control, etc.)
#
# LumiX provides all of these while maintaining similar expressiveness.
#
# ========================================================================
# TO RUN THIS MODEL:
# ========================================================================
#
# Option 1: Using GLPK (free, open-source)
#   1. Install GLPK: brew install glpk (Mac) or apt-get install glpk-utils (Linux)
#   2. Solve: glpsol --model diet_problem.mod --output diet_solution.txt
#
# Option 2: Using AMPL Community Edition (free for small problems)
#   1. Download from: https://ampl.com/ce/
#   2. ampl: model diet_problem.mod;
#   3. ampl: option solver glpk;
#   4. ampl: solve;
#   5. ampl: display X_Oatmeal, X_Chicken, X_Eggs, X_Milk, X_ApplePie, X_Pork;
#
# Option 3: Using online solvers
#   - NEOS Server: https://neos-server.org/neos/
#   - Upload model and solve online
#
# Compare with LumiX:
#   pip install lumix[ortools]
#   python basic_lp.py
#   (Simpler, more integrated, better output formatting)
#
# ========================================================================
# CONCLUSION:
# ========================================================================
#
# AMPL is a good middle ground:
# - Modern enough for current use (unlike LINDO)
# - Works with free solvers (unlike LINGO)
# - Algebraic and declarative
# - Widely taught and used
#
# But for software development projects, LumiX offers:
# - Better integration with modern tools
# - Type safety and IDE support
# - Data-driven approach (cleaner separation)
# - Full Python ecosystem
# - More maintainable for large projects
#
# AMPL is excellent for:
# - Academic optimization courses
# - Rapid prototyping of mathematical models
# - When you need a pure modeling language
# - Working with multiple solver backends
#
# LumiX is better for:
# - Production software systems
# - When data comes from databases/APIs
# - Team development with version control
# - Integration with data science workflows
# - Modern software engineering practices
#
# ========================================================================
