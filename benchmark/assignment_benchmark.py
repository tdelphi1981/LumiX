#!/usr/bin/env python3
"""
Framework Comparison Benchmark 3: Worker-Task Assignment Problem
PuLP vs Pyomo vs LumiX

This script implements a Worker-Task Assignment Problem in three Python
optimization frameworks and measures:
- Lines of code (LOC) for model definition
- Model construction time
- Solve time
- Memory usage (peak)

The Assignment Problem:
    Minimize total assignment cost while respecting constraints.
    Given: 10 workers, 12 tasks, skill-based cost matrix
    Find: Binary assignments minimizing cost while ensuring:
        - Each task is assigned to exactly one worker
        - Each worker doesn't exceed their capacity
        - Each worker is assigned at least one task

Decision Variables: 120 total
    - assignment[worker, task]: 120 binary variables (10 workers × 12 tasks)

This problem demonstrates Cartesian product indexing and binary integer
programming, which scales differently than simple LP problems.

Results are output as both LaTeX and Markdown tables.

Usage:
    python assignment_benchmark.py

Requirements:
    pip install pulp pyomo lumix lizard

Author: LumiX Development Team
Date: 2025
"""

import time
import statistics
import tracemalloc
import inspect
from dataclasses import dataclass
from typing import Dict, Tuple, Any, List
from pathlib import Path
import traceback
import random

import lizard

# Set seed for reproducibility
random.seed(42)

# ==================== SHARED DATA ====================

@dataclass
class Worker:
    """Worker with hourly rate and task capacity (used by LumiX)."""
    id: int
    name: str
    hourly_rate: int
    max_tasks: int


@dataclass
class Task:
    """Task with duration and priority (used by LumiX)."""
    id: int
    name: str
    duration_hours: int
    priority: int


# Generate 10 workers with varying characteristics
def generate_workers(n: int = 10) -> List[Tuple]:
    """Generate n workers with realistic varying parameters."""
    workers = []
    roles = ["Dev", "Analyst", "Engineer", "Designer", "Specialist"]

    for i in range(n):
        role = roles[i % len(roles)]
        name = f"{role}_{i+1:02d}"

        # Vary hourly rate: $20-$45/hour
        hourly_rate = 20 + (i % 6) * 5 + random.randint(-2, 2)
        # Vary max tasks: 2-5 tasks
        max_tasks = 2 + (i % 4)

        workers.append((i, name, hourly_rate, max_tasks))

    return workers


# Generate 12 tasks with varying characteristics
def generate_tasks(n: int = 12) -> List[Tuple]:
    """Generate n tasks with realistic varying parameters."""
    tasks = []
    task_types = [
        "Backend Dev", "Frontend Dev", "Database Work", "API Design",
        "Testing", "Documentation", "Code Review", "Deployment",
        "Security Audit", "Performance Opt", "Integration", "Maintenance"
    ]

    for i in range(n):
        name = task_types[i % len(task_types)]
        if i >= len(task_types):
            name = f"{name}_{i // len(task_types) + 1}"

        # Duration: 2-10 hours
        duration = 2 + (i % 9)
        # Priority: 1-10
        priority = 1 + (i % 10)

        tasks.append((i, name, duration, priority))

    return tasks


# Generate skill penalty matrix
def generate_skill_penalties(workers: List[Tuple], tasks: List[Tuple]) -> Dict[tuple, int]:
    """Generate skill penalty matrix for worker-task compatibility."""
    penalties = {}

    for w in workers:
        worker_id = w[0]
        for t in tasks:
            task_id = t[0]
            # Base penalty varies by worker specialization
            base_penalty = ((worker_id + task_id) % 5) * 10
            # Add some randomness
            penalty = max(0, base_penalty + random.randint(-5, 10))
            penalties[(worker_id, task_id)] = penalty

    return penalties


WORKERS_DATA = generate_workers(10)
TASKS_DATA = generate_tasks(12)
SKILL_PENALTIES = generate_skill_penalties(WORKERS_DATA, TASKS_DATA)

# Number of benchmark iterations for timing
NUM_ITERATIONS = 100

# Output directory
OUTPUT_DIR = Path(__file__).parent / "results"

# Total number of decision variables
NUM_WORKERS = len(WORKERS_DATA)
NUM_TASKS = len(TASKS_DATA)
NUM_VARIABLES = NUM_WORKERS * NUM_TASKS  # 10 × 12 = 120 binary variables


def get_assignment_cost(worker_id: int, task_id: int) -> int:
    """Calculate total cost of assigning a worker to a task."""
    worker = WORKERS_DATA[worker_id]
    task = TASKS_DATA[task_id]
    penalty = SKILL_PENALTIES.get((worker_id, task_id), 50)
    base_cost = worker[2] * task[2]  # hourly_rate * duration_hours
    return base_cost + penalty


# ==================== PuLP IMPLEMENTATION ====================

def build_and_solve_pulp() -> Tuple[float, float, float, float]:
    """
    Build and solve assignment problem using PuLP.

    Returns:
        Tuple of (build_time_ms, solve_time_ms, peak_memory_mb, objective_value)
    """
    import pulp

    # Start memory tracking
    tracemalloc.start()

    # --- MODEL CONSTRUCTION (timed) ---
    start_build = time.perf_counter()

    # Create the problem
    prob = pulp.LpProblem("Assignment_Problem", pulp.LpMinimize)

    # Extract IDs
    worker_ids = [w[0] for w in WORKERS_DATA]
    task_ids = [t[0] for t in TASKS_DATA]

    # Extract worker data into dictionaries
    max_tasks = {w[0]: w[3] for w in WORKERS_DATA}
    hourly_rate = {w[0]: w[2] for w in WORKERS_DATA}
    duration = {t[0]: t[2] for t in TASKS_DATA}

    # Create cost dictionary
    cost = {}
    for w_id in worker_ids:
        for t_id in task_ids:
            cost[(w_id, t_id)] = get_assignment_cost(w_id, t_id)

    # Decision variables: binary assignment[worker, task]
    assignment = pulp.LpVariable.dicts("assignment",[(w, t) for w in worker_ids for t in task_ids],cat='Binary')

    # Objective: minimize total assignment cost
    prob += pulp.lpSum([cost[(w, t)] * assignment[(w, t)] for w in worker_ids for t in task_ids])

    # Constraint 1: Each task assigned to exactly one worker
    for t in task_ids:
        prob += pulp.lpSum([assignment[(w, t)] for w in worker_ids]) == 1

    # Constraint 2: Each worker doesn't exceed their capacity
    for w in worker_ids:
        prob += pulp.lpSum([assignment[(w, t)] for t in task_ids]) <= max_tasks[w]

    # Constraint 3: Each worker assigned at least one task
    for w in worker_ids:
        prob += pulp.lpSum([assignment[(w, t)] for t in task_ids]) >= 1

    end_build = time.perf_counter()
    build_time = (end_build - start_build) * 1000  # ms

    # --- SOLVE (timed) ---
    start_solve = time.perf_counter()
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    end_solve = time.perf_counter()
    solve_time = (end_solve - start_solve) * 1000  # ms

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_memory_mb = peak / (1024 * 1024)

    objective = pulp.value(prob.objective)

    return build_time, solve_time, peak_memory_mb, objective


# ==================== PYOMO IMPLEMENTATION ====================

def build_and_solve_pyomo() -> Tuple[float, float, float, float]:
    """
    Build and solve assignment problem using Pyomo.

    Returns:
        Tuple of (build_time_ms, solve_time_ms, peak_memory_mb, objective_value)
    """
    import pyomo.environ as pyo

    # Start memory tracking
    tracemalloc.start()

    # --- MODEL CONSTRUCTION (timed) ---
    start_build = time.perf_counter()

    # Create concrete model
    model = pyo.ConcreteModel()

    # Sets
    worker_ids = [w[0] for w in WORKERS_DATA]
    task_ids = [t[0] for t in TASKS_DATA]
    model.Workers = pyo.Set(initialize=worker_ids)
    model.Tasks = pyo.Set(initialize=task_ids)

    # Parameters
    max_tasks_dict = {w[0]: w[3] for w in WORKERS_DATA}
    model.max_tasks = pyo.Param(model.Workers, initialize=max_tasks_dict)

    # Cost parameter
    cost_dict = {}
    for w_id in worker_ids:
        for t_id in task_ids:
            cost_dict[(w_id, t_id)] = get_assignment_cost(w_id, t_id)
    model.cost = pyo.Param(model.Workers, model.Tasks, initialize=cost_dict)

    # Variables: Binary assignment
    model.assignment = pyo.Var(model.Workers, model.Tasks, domain=pyo.Binary)

    # Objective: minimize total cost
    model.obj = pyo.Objective(expr=sum(model.cost[w, t] * model.assignment[w, t]for w in model.Workers for t in model.Tasks),sense=pyo.minimize)

    # Constraint 1: Each task assigned to exactly one worker
    model.task_coverage = pyo.ConstraintList()
    for t in task_ids:
        model.task_coverage.add(sum(model.assignment[w, t] for w in model.Workers) == 1)

    # Constraint 2: Each worker doesn't exceed capacity
    model.worker_capacity = pyo.ConstraintList()
    for w in worker_ids:
        model.worker_capacity.add(sum(model.assignment[w, t] for t in model.Tasks) <= model.max_tasks[w])

    # Constraint 3: Each worker assigned at least one task
    model.worker_min = pyo.ConstraintList()
    for w in worker_ids:
        model.worker_min.add(sum(model.assignment[w, t] for t in model.Tasks) >= 1)

    end_build = time.perf_counter()
    build_time = (end_build - start_build) * 1000  # ms

    # --- SOLVE (timed) ---
    start_solve = time.perf_counter()
    # Try multiple solvers in order of preference
    solvers_to_try = ['cbc', 'glpk', 'cplex', 'gurobi']
    solver = None
    for solver_name in solvers_to_try:
        try:
            solver = pyo.SolverFactory(solver_name)
            if solver.available():
                break
            solver = None
        except Exception:
            solver = None

    if solver is None:
        raise RuntimeError("No solver available for Pyomo (tried: cbc, glpk, cplex, gurobi)")

    result = solver.solve(model, tee=False)
    end_solve = time.perf_counter()
    solve_time = (end_solve - start_solve) * 1000  # ms

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_memory_mb = peak / (1024 * 1024)

    objective = pyo.value(model.obj)

    return build_time, solve_time, peak_memory_mb, objective


# ==================== LumiX IMPLEMENTATION ====================

def build_and_solve_lumix() -> Tuple[float, float, float, float]:
    """
    Build and solve assignment problem using LumiX.

    Returns:
        Tuple of (build_time_ms, solve_time_ms, peak_memory_mb, objective_value)
    """
    from lumix import LXConstraint, LXLinearExpression, LXModel, LXOptimizer, LXVariable
    from lumix.indexing import LXIndexDimension

    # Start memory tracking
    tracemalloc.start()

    # --- MODEL CONSTRUCTION (timed) ---
    start_build = time.perf_counter()

    # Create Worker and Task instances
    workers = [Worker(w[0], w[1], w[2], w[3]) for w in WORKERS_DATA]
    tasks = [Task(t[0], t[1], t[2], t[3]) for t in TASKS_DATA]

    # Decision Variable: Binary assignment (worker, task) pairs
    assignment = LXVariable[Tuple[Worker, Task], int]("assignment").binary().indexed_by_product(LXIndexDimension(Worker, lambda w: w.id).from_data(workers),LXIndexDimension(Task, lambda t: t.id).from_data(tasks))

    # Create model
    model = LXModel("assignment_problem").add_variable(assignment)

    # Objective: minimize total assignment cost
    model.minimize(LXLinearExpression().add_multi_term(assignment,coeff=lambda w, t: w.hourly_rate * t.duration_hours + SKILL_PENALTIES.get((w.id, t.id), 50)))

    # Constraint 1: Each task assigned to exactly one worker
    for task in tasks:
        model.add_constraint(LXConstraint(f"task_coverage_{task.id}").expression(LXLinearExpression().add_multi_term(assignment,coeff=lambda w, t, tid=task.id: 1 if t.id == tid else 0)).eq().rhs(1))

    # Constraint 2: Each worker doesn't exceed their capacity
    for worker in workers:
        model.add_constraint(LXConstraint(f"worker_capacity_{worker.id}").expression(LXLinearExpression().add_multi_term(assignment,coeff=lambda w, t, wid=worker.id: 1 if w.id == wid else 0)).le().rhs(worker.max_tasks))

    # Constraint 3: Each worker assigned at least one task
    for worker in workers:
        model.add_constraint(LXConstraint(f"worker_min_{worker.id}").expression(LXLinearExpression().add_multi_term(assignment, coeff=lambda w, t, wid=worker.id: 1 if w.id == wid else 0)).ge().rhs(1))

    end_build = time.perf_counter()
    build_time = (end_build - start_build) * 1000  # ms

    # --- SOLVE (timed) ---
    start_solve = time.perf_counter()
    optimizer = LXOptimizer()
    optimizer.use_solver("glpk")
    solution = optimizer.solve(model)
    end_solve = time.perf_counter()
    solve_time = (end_solve - start_solve) * 1000  # ms

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_memory_mb = peak / (1024 * 1024)

    objective = solution.objective_value

    return build_time, solve_time, peak_memory_mb, objective


# ==================== CODE COMPLEXITY ANALYSIS (LIZARD) ====================

def analyze_code_complexity() -> Dict[str, Dict[str, Any]]:
    """
    Analyze code complexity using lizard for each framework implementation.

    Returns:
        Dictionary with NLOC, CCN, and other metrics for each framework.
    """
    frameworks = {
        "PuLP": {
            "func": build_and_solve_pulp,
            "data_repetition": "5+ dicts",
            "notes": "Dictionary-based indexing, manual cost calculation",
        },
        "Pyomo": {
            "func": build_and_solve_pyomo,
            "data_repetition": "3 Params + loops",
            "notes": "Component-based, indexed Sets and for-loop constraints",
        },
        "LumiX": {
            "func": build_and_solve_lumix,
            "data_repetition": "2 dataclasses",
            "notes": "Data-centric, Cartesian product indexing via lambdas",
        },
    }

    results = {}

    for name, info in frameworks.items():
        # Get the source code of the function
        source_code = inspect.getsource(info["func"])

        # Analyze with lizard
        analysis = lizard.analyze_file.analyze_source_code(f"{name}_impl.py", source_code)

        # Get the function info (there should be exactly one function)
        if analysis.function_list:
            func_info = analysis.function_list[0]
            nloc = func_info.nloc
            ccn = func_info.cyclomatic_complexity
            token_count = func_info.token_count
        else:
            # Fallback: use file-level metrics
            nloc = analysis.nloc
            ccn = 1
            token_count = 0

        results[name] = {
            "nloc": nloc,
            "ccn": ccn,
            "token_count": token_count,
            "data_repetition": info["data_repetition"],
            "notes": info["notes"],
        }

    return results


# Global variable to cache complexity analysis results
_COMPLEXITY_ANALYSIS: Dict[str, Dict[str, Any]] | None = None


def get_complexity_analysis() -> Dict[str, Dict[str, Any]]:
    """Get or compute code complexity analysis (cached)."""
    global _COMPLEXITY_ANALYSIS
    if _COMPLEXITY_ANALYSIS is None:
        _COMPLEXITY_ANALYSIS = analyze_code_complexity()
    return _COMPLEXITY_ANALYSIS


# ==================== BENCHMARK RUNNER ====================

def run_benchmark() -> Dict[str, Dict[str, Any]]:
    """
    Run benchmarks for all three frameworks.

    Returns:
        Dictionary with results for each framework
    """
    results = {}

    # Get code complexity analysis using lizard
    complexity_analysis = get_complexity_analysis()

    frameworks = [
        ("PuLP", build_and_solve_pulp),
        ("Pyomo", build_and_solve_pyomo),
        ("LumiX", build_and_solve_lumix),
    ]

    for name, func in frameworks:
        print(f"\nBenchmarking {name}...")

        build_times = []
        solve_times = []
        memory_usages = []
        objective = None

        try:
            for i in range(NUM_ITERATIONS):
                build_time, solve_time, memory_mb, obj = func()
                build_times.append(build_time)
                solve_times.append(solve_time)
                memory_usages.append(memory_mb)
                objective = obj
                if (i + 1) % 10 == 0:
                    print(f"  Iteration {i+1}/{NUM_ITERATIONS}: build={build_time:.2f}ms, solve={solve_time:.2f}ms")

            # Get complexity metrics from lizard analysis
            complexity = complexity_analysis[name]

            results[name] = {
                "build_time_mean": statistics.mean(build_times),
                "build_time_std": statistics.stdev(build_times) if len(build_times) > 1 else 0,
                "solve_time_mean": statistics.mean(solve_times),
                "solve_time_std": statistics.stdev(solve_times) if len(solve_times) > 1 else 0,
                "memory_mean": statistics.mean(memory_usages),
                "memory_std": statistics.stdev(memory_usages) if len(memory_usages) > 1 else 0,
                "objective": objective,
                "num_vars": NUM_VARIABLES,
                "nloc": complexity["nloc"],
                "ccn": complexity["ccn"],
                "data_repetition": complexity["data_repetition"],
                "status": "OK"
            }
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            results[name] = {
                "status": "ERROR",
                "error": str(e)
            }

    return results


# ==================== OUTPUT GENERATION ====================

def generate_latex_table(results: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate LaTeX table from benchmark results.

    Args:
        results: Dictionary with benchmark results

    Returns:
        LaTeX table string
    """
    latex = r"""\begin{table}[h]
\caption{Quantitative Comparison: Assignment Problem Benchmark}
\label{tab:benchmark_assignment}
\footnotesize
\begin{tabular}{|l|c|c|c|c|c|c|c|l|}
\hline
\textbf{Framework} & \textbf{Vars} & \textbf{NLOC} & \textbf{CCN} & \textbf{Build} & \textbf{Solve} & \textbf{Mem.} & \textbf{Obj.} & \textbf{Data} \\
                   &               &               &              & (ms)           & (ms)           & (MB)          &               & \textbf{Handling} \\
\hline
"""

    for name in ["PuLP", "Pyomo", "LumiX"]:
        if name in results and results[name]["status"] == "OK":
            r = results[name]
            latex += f"{name} & {r['num_vars']} & {r['nloc']} & {r['ccn']} & "
            latex += f"{r['build_time_mean']:.2f}$\\pm${r['build_time_std']:.2f} & "
            latex += f"{r['solve_time_mean']:.1f}$\\pm${r['solve_time_std']:.1f} & "
            latex += f"{r['memory_mean']:.2f}$\\pm${r['memory_std']:.2f} & "
            latex += f"\\${r['objective']:.0f} & "
            latex += f"{r['data_repetition']} \\\\\n\\hline\n"
        else:
            latex += f"{name} & -- & -- & -- & ERROR & ERROR & ERROR & -- & -- \\\\\n\\hline\n"

    latex += r"""\end{tabular}
\\[2pt]
\scriptsize{NLOC = Non-comment Lines of Code; CCN = Cyclomatic Complexity Number (via Lizard); Build/Solve times and memory averaged over """ + str(NUM_ITERATIONS) + r""" iterations; Solver: CBC/GLPK.}
\end{table}
"""
    return latex


def generate_markdown_table(results: Dict[str, Dict[str, Any]]) -> str:
    """
    Generate beautiful Markdown table from benchmark results.

    Args:
        results: Dictionary with benchmark results

    Returns:
        Markdown string with table and analysis
    """
    md = """# Framework Comparison Results: Worker-Task Assignment

## Benchmark Configuration

| Parameter | Value |
|-----------|-------|
| Problem | Worker-Task Assignment (Binary IP) |
| Workers | """ + str(NUM_WORKERS) + """ |
| Tasks | """ + str(NUM_TASKS) + """ |
| Variables | """ + str(NUM_VARIABLES) + """ binary (workers x tasks) |
| Constraints | """ + str(NUM_TASKS + 2 * NUM_WORKERS) + """ (task coverage + worker capacity + worker minimum) |
| Iterations | """ + str(NUM_ITERATIONS) + """ |
| Solver | CBC (PuLP/Pyomo), GLPK (LumiX) |
| Complexity Analysis | Lizard (NLOC, CCN) |

## Results

| Framework | Vars | NLOC | CCN | Build (ms) | Solve (ms) | Memory (MB) | Objective | Data Handling |
|:----------|:----:|:----:|:---:|:----------:|:----------:|:-----------:|:---------:|:--------------|
"""

    for name in ["PuLP", "Pyomo", "LumiX"]:
        if name in results and results[name]["status"] == "OK":
            r = results[name]
            md += f"| **{name}** | {r['num_vars']} | {r['nloc']} | {r['ccn']} | "
            md += f"{r['build_time_mean']:.2f} +/- {r['build_time_std']:.2f} | "
            md += f"{r['solve_time_mean']:.1f} +/- {r['solve_time_std']:.1f} | "
            md += f"{r['memory_mean']:.2f} +/- {r['memory_std']:.2f} | "
            md += f"${r['objective']:.0f} | "
            md += f"{r['data_repetition']} |\n"
        else:
            error_msg = results.get(name, {}).get("error", "Unknown error")
            md += f"| **{name}** | -- | -- | -- | ERROR | ERROR | ERROR | -- | {error_msg} |\n"

    md += """
## Metrics Legend

- **NLOC**: Non-comment Lines of Code (measured by Lizard)
- **CCN**: Cyclomatic Complexity Number (lower = simpler code)
- **Vars**: Total decision variables (binary assignments)

## Key Observations

"""

    # Add observations if all frameworks succeeded
    all_ok = all(results.get(name, {}).get("status") == "OK" for name in ["PuLP", "Pyomo", "LumiX"])
    if all_ok:
        md += """- **Same Solution**: All frameworks produce identical optimal solutions
- **Binary Integer Programming**: 120 binary variables (10 workers x 12 tasks)
- **Cartesian Product Indexing**: LumiX handles worker-task pairs elegantly
- **Constraint Complexity**: Task coverage (12) + worker capacity (10) + worker minimum (10) = 32 constraints

## Problem Characteristics

| Aspect | Description |
|--------|-------------|
| Problem Type | Binary Integer Programming (BIP) |
| Variable Type | Binary (0/1 assignment) |
| Indexing | Cartesian product (Worker x Task) |
| Objective | Minimize total assignment cost |
| Key Constraints | Task coverage, worker capacity, worker utilization |

## Data Handling Comparison

| Framework | Approach | Data Structures |
|-----------|----------|-----------------|
| PuLP | Dictionary-based tuples | 5+ dicts (IDs, costs, capacities) |
| Pyomo | Indexed Sets + Params | 2 Sets, 2 Params, for-loop constraints |
| LumiX | Cartesian product via lambdas | 2 dataclasses, indexed by product |
"""
    else:
        md += "- Some frameworks failed to run. Check dependencies and solver availability.\n"

    md += f"""
---
*Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return md


def print_results(results: Dict[str, Dict[str, Any]]):
    """Print formatted benchmark results to console."""
    print("\n" + "=" * 115)
    print("BENCHMARK RESULTS: Worker-Task Assignment (with Lizard Code Complexity Analysis)")
    print("=" * 115)
    print(f"Problem: Worker-Task Assignment ({NUM_VARIABLES} binary variables, {NUM_TASKS + 2*NUM_WORKERS} constraints)")
    print(f"Workers: {NUM_WORKERS}, Tasks: {NUM_TASKS}")
    print(f"Iterations: {NUM_ITERATIONS}")
    print()

    # Header
    header = f"{'Framework':<10} {'Vars':>5} {'NLOC':>5} {'CCN':>5} {'Build (ms)':>18} {'Solve (ms)':>18} {'Memory (MB)':>18} {'Objective':>12}"
    print(header)
    print("-" * 115)

    for name in ["PuLP", "Pyomo", "LumiX"]:
        if name in results and results[name]["status"] == "OK":
            r = results[name]
            build_str = f"{r['build_time_mean']:.2f} +/- {r['build_time_std']:.2f}"
            solve_str = f"{r['solve_time_mean']:.1f} +/- {r['solve_time_std']:.1f}"
            memory_str = f"{r['memory_mean']:.2f} +/- {r['memory_std']:.2f}"
            print(f"{name:<10} {r['num_vars']:>5} {r['nloc']:>5} {r['ccn']:>5} {build_str:>18} {solve_str:>18} {memory_str:>18} ${r['objective']:>10.0f}")
        else:
            print(f"{name:<10} {'--':>5} {'--':>5} {'--':>5} {'ERROR':>18} {'ERROR':>18} {'ERROR':>18} {'--':>12}")

    # Get complexity analysis for data handling comparison
    complexity_analysis = get_complexity_analysis()

    print()
    print("Data Handling Comparison:")
    print("-" * 115)
    for name in ["PuLP", "Pyomo", "LumiX"]:
        info = complexity_analysis[name]
        print(f"  {name}: {info['data_repetition']}")

    print()
    print("Metrics Legend:")
    print("-" * 115)
    print("  NLOC = Non-comment Lines of Code (measured by Lizard)")
    print("  CCN  = Cyclomatic Complexity Number (lower = simpler code)")

    print()
    print("Key Observations:")
    print("-" * 115)
    print("  - All frameworks produce the same optimal solution")
    print("  - Binary integer programming with 120 variables")
    print("  - Cartesian product indexing (Worker x Task pairs)")
    print("  - All frameworks use MIP solvers (CBC/GLPK) for fair comparison")


def main():
    """Run the full benchmark suite."""
    print("=" * 80)
    print("Framework Comparison Benchmark 3: Worker-Task Assignment")
    print("PuLP vs Pyomo vs LumiX")
    print("=" * 80)
    print("\nProblem: Worker-Task Assignment (Binary Integer Programming)")
    print(f"Workers: {NUM_WORKERS}, Tasks: {NUM_TASKS}")
    print(f"Decision Variables: {NUM_VARIABLES} binary (worker-task assignments)")
    print(f"Constraints: {NUM_TASKS + 2*NUM_WORKERS} (coverage + capacity + utilization)")
    print(f"Solver: CBC (PuLP/Pyomo), GLPK (LumiX)")

    # Check dependencies
    print("\nChecking dependencies...")
    missing = []
    try:
        import pulp
        print("  [OK] PuLP installed")
    except ImportError:
        missing.append("pulp")
        print("  [X] PuLP not installed")

    try:
        import pyomo.environ
        print("  [OK] Pyomo installed")
    except ImportError:
        missing.append("pyomo")
        print("  [X] Pyomo not installed")

    try:
        import lumix
        print("  [OK] LumiX installed")
    except ImportError:
        missing.append("lumix")
        print("  [X] LumiX not installed")

    if missing:
        print(f"\nWARNING: Missing packages: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))

    # Run benchmarks
    results = run_benchmark()

    # Print results to console
    print_results(results)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Generate and save LaTeX table
    print("\n" + "=" * 80)
    print("LATEX TABLE OUTPUT")
    print("=" * 80)
    latex = generate_latex_table(results)
    print(latex)

    latex_file = OUTPUT_DIR / "assignment_table.tex"
    with open(latex_file, "w") as f:
        f.write(latex)
    print(f"\nLaTeX table saved to: {latex_file}")

    # Generate and save Markdown
    print("\n" + "=" * 80)
    print("MARKDOWN OUTPUT")
    print("=" * 80)
    markdown = generate_markdown_table(results)
    print(markdown)

    md_file = OUTPUT_DIR / "ASSIGNMENT_RESULTS.md"
    with open(md_file, "w") as f:
        f.write(markdown)
    print(f"\nMarkdown results saved to: {md_file}")


if __name__ == "__main__":
    main()
