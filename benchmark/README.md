# LumiX Framework Comparison Benchmark

This benchmark compares **LumiX** against two popular Python optimization frameworks: **PuLP** and **Pyomo**.

## Problem Description

The benchmark uses the classic **Diet Problem** - a fundamental linear programming problem:

> **Objective**: Minimize the cost of food while meeting nutritional requirements.
>
> **Given**: 6 foods with cost and nutritional content (calories, protein, calcium)
>
> **Find**: Servings of each food that minimize total cost while meeting daily minimums

## Metrics Measured

| Metric | Description |
|--------|-------------|
| **LOC** | Lines of code for model definition |
| **Build Time** | Time to construct the optimization model |
| **Solve Time** | Time to solve the model |
| **Memory Usage** | Peak memory consumption (via `tracemalloc`) |
| **Objective Value** | Optimal solution value |

## Requirements

```bash
pip install pulp pyomo lumix-opt
```

You also need a solver installed. The benchmark uses **GLPK** or **CBC**:

```bash
# macOS
brew install glpk

# Ubuntu/Debian
sudo apt-get install glpk-utils

# Or use conda
conda install -c conda-forge glpk
```

## Usage

```bash
cd benchmark
python framework_comparison.py
```

## Output

The benchmark generates two output files in the `results/` folder:

| File | Format | Purpose |
|------|--------|---------|
| `benchmark_table.tex` | LaTeX | For academic papers |
| `RESULTS.md` | Markdown | For documentation/README |

## Sample Results

| Framework | LOC | Build (ms) | Solve (ms) | Memory (MB) | Objective | Data Handling |
|:----------|:---:|:----------:|:----------:|:-----------:|:---------:|:--------------|
| **PuLP** | 15 | 0.12 +/- 0.04 | 15.6 +/- 0.9 | 0.45 +/- 0.02 | $5.90 | 4 separate dicts |
| **Pyomo** | 22 | 0.29 +/- 0.24 | 2.6 +/- 2.9 | 1.82 +/- 0.15 | $5.90 | 4 Param objects |
| **LumiX** | 18 | 0.02 +/- 0.03 | 0.4 +/- 0.9 | 0.38 +/- 0.01 | $5.90 | 1 dataclass |

> **Note**: Actual results will vary based on your system configuration and solver version.

## Key Findings

### All Frameworks Produce Identical Solutions

The optimal solution minimizes food cost to **$5.90** while meeting all nutritional constraints.

### Data Handling Comparison

| Framework | Approach | Data Repetition |
|-----------|----------|-----------------|
| **PuLP** | Dictionary-based indexing | Data extracted into 4 separate dicts |
| **Pyomo** | Component-based AML | Data stored in 4 Param objects |
| **LumiX** | Data-centric with lambdas | Single dataclass, coefficients via lambdas |

### LumiX Advantages

1. **DRY Principle**: Data defined once in a dataclass
2. **Type Safety**: IDE autocompletion via typed lambda coefficients
3. **Readability**: Fluent API with method chaining
4. **Low Memory**: Minimal overhead for model construction

## File Structure

```
benchmark/
  framework_comparison.py   # Main benchmark script
  README.md                  # This file
  results/
    benchmark_table.tex      # LaTeX output (generated)
    RESULTS.md               # Markdown output (generated)
```

## Customization

You can modify the benchmark by editing `framework_comparison.py`:

- `FOODS_DATA`: Change the problem data
- `MIN_CALORIES`, `MIN_PROTEIN`, `MIN_CALCIUM`: Adjust constraints
- `NUM_ITERATIONS`: Change number of timing iterations

## License

This benchmark is part of the LumiX project, licensed under the Academic Free License v3.0.