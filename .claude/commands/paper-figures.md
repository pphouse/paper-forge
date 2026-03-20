# Paper Figures

Generate data visualizations for the paper using matplotlib/seaborn.

## Usage

```
/paper-figures <project_dir>
```

## What This Does

1. Reads the paper_spec.yaml to identify required figures
2. Reads the experiment data to get actual values
3. Generates publication-quality figures:
   - Bar charts for comparisons
   - Line plots for trends
   - ROC curves for classification results
   - Confusion matrices
   - Box/violin plots for distributions
   - Heatmaps for correlations

4. Saves figures to `<project_dir>/figures/`

## Figure Types

| Type | Use Case | Data Format |
|------|----------|-------------|
| `bar` | Model comparison | `{"labels": [...], "values": [...]}` |
| `line` | Trends over time | `{"x": [...], "y": [...]}` |
| `roc_curve` | Classification | `{"y_true": [...], "y_prob": [...]}` |
| `confusion_matrix` | Classification | `{"y_true": [...], "y_pred": [...]}` |
| `box` / `violin` | Distributions | `{"groups": {"A": [...], "B": [...]}}` |
| `heatmap` | Correlations | `{"matrix": [[...]], "labels": [...]}` |
| `scatter` | Relationships | `{"x": [...], "y": [...]}` |

## Example Code

```python
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import roc_curve, auc

# Load experiment data
df = pd.read_csv('results.csv')

# Generate ROC curve
y_true = df['label'].values
y_prob = df['pred_prob'].values
fpr, tpr, _ = roc_curve(y_true, y_prob)
roc_auc = auc(fpr, tpr)

fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(fpr, tpr, lw=2, label=f'AUC = {roc_auc:.3f}')
ax.plot([0, 1], [0, 1], 'k--')
ax.set_xlabel('False Positive Rate')
ax.set_ylabel('True Positive Rate')
ax.legend()
plt.savefig('figures/fig_roc.png', dpi=300, bbox_inches='tight')
```

## Style Guidelines

- Use consistent color schemes
- Include proper axis labels
- Add legends where appropriate
- Export at 300 DPI for publication quality
- Use `bbox_inches='tight'` to avoid cropping
