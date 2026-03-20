# Paper Analyze

Analyze an experiment directory and generate a data analysis report.

## Usage

```
/paper-analyze <experiment_dir>
```

## What This Does

1. Scans the experiment directory for:
   - Data files (CSV, JSON, YAML, TSV, XLSX)
   - Images (PNG, JPG, SVG)
   - Documents (MD, TXT, logs)
   - Code files (Python, R, Jupyter notebooks)

2. Analyzes each data file:
   - Column statistics (mean, std, min, max)
   - Data types
   - Missing values
   - Suggested figure types

3. Outputs a structured analysis report

## Example

```
/paper-analyze ./experiments/model_results/
```

## Implementation

```python
from paperclaw.pipeline import Pipeline
from paperclaw.experiment_collector import ExperimentCollector

# Collect experiment data
collector = ExperimentCollector("$ARGUMENTS")
collected = collector.collect()

# Analyze data files
pipeline = Pipeline("./temp_analysis")
for data_file in collected["data_files"]:
    analysis = pipeline.analyze_data(data_file)
    print(f"## {data_file.name}")
    print(analysis)

# Print summary
print(collector.summarise(collected))
```
