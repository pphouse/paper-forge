# Paper Analyze

Analyze an experiment directory and generate a comprehensive data analysis report.

## Usage

```
/paper-analyze <experiment_dir>
```

## What This Does

1. **Directory Scanning** - Recursively scans for:
   - Data files: `.csv`, `.json`, `.yaml`, `.tsv`, `.xlsx`
   - Images: `.png`, `.jpg`, `.svg`, `.tiff`
   - Documents: `.md`, `.txt`, `.log`, `.docx`, `.pdf`
   - Code: `.py`, `.r`, `.jl`, `.ipynb`

2. **Data Analysis** - For each data file:
   - Column statistics (mean, std, min, max, percentiles)
   - Data types and cardinality
   - Missing value analysis
   - Distribution characteristics
   - Correlation analysis (if applicable)

3. **ML Results Detection** - Automatically identifies:
   - Train/valid/test splits
   - Cross-validation folds
   - Prediction columns (pred, pred_prob, score)
   - Label columns (label, target, y, class)
   - Model performance metrics

4. **Output Report** - Structured analysis including:
   - Dataset summary statistics
   - Key findings and metrics
   - Suggested figure types
   - Data quality issues

## Example

```
/paper-analyze ./experiments/model_results/
```

## Implementation Steps

When executing this skill, Claude Code should:

1. **List directory contents**
   ```bash
   find <experiment_dir> -type f \( -name "*.csv" -o -name "*.json" -o -name "*.yaml" \)
   ```

2. **Analyze each data file**
   ```python
   import pandas as pd
   from sklearn.metrics import roc_auc_score, accuracy_score

   df = pd.read_csv(filepath)
   print(df.describe())
   print(df.info())

   # If prediction columns exist
   if 'pred_prob' in df.columns and 'label' in df.columns:
       auc = roc_auc_score(df['label'], df['pred_prob'])
       print(f"AUC: {auc:.4f}")
   ```

3. **Identify cross-validation folds**
   - Look for `fold` column or `results_0_*.csv`, `results_1_*.csv` patterns
   - Calculate per-fold and overall metrics

4. **Check for institution/group columns**
   - Calculate group-wise statistics
   - Identify any systematic differences

5. **Generate summary report**
   - Key metrics with confidence intervals
   - Sample sizes and distributions
   - Recommendations for paper content

## Output Format

```markdown
## Data Analysis Report

### Files Found
- Data files: 12
- Image files: 3
- Document files: 2

### Dataset Summary
- Total samples: 12,423
- Unique patients: 4,141
- Positive class: 927 (7.46%)

### Model Performance
- Overall AUC: 0.857
- Mean AUC (3-fold CV): 0.864 ± 0.008
- Accuracy: 93.2%

### Institution Distribution
| Institution | N | Positive (%) | AUC |
|------------|---|-------------|-----|
| Kyushu | 2,154 | 6.4% | 0.887 |
| ... | ... | ... | ... |

### Suggested Figures
1. ROC curve (per-fold + overall)
2. Institution comparison bar chart
3. Confusion matrix
4. Feature importance (if available)
```

## Notes

- Run this BEFORE `/paper-generate` to gather data context
- Save the analysis output for reference during paper writing
- Identify any data quality issues early
