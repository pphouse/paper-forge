# Paper Figures

Generate publication-quality data visualizations for the paper.

## Usage

```
/paper-figures <project_dir>
```

## What This Does

1. Reads `paper_spec.yaml` to identify required figures
2. Loads experiment data to get actual values
3. Generates publication-quality figures (300 DPI)
4. Saves to `<project_dir>/figures/`

## Figure Types

| Type | Use Case | When to Use |
|------|----------|-------------|
| `roc_curve` | Classification performance | Binary/multiclass classification |
| `confusion_matrix` | Prediction breakdown | Show TP/TN/FP/FN |
| `bar_chart` | Group comparisons | Institution/model comparison |
| `line_plot` | Trends over time | Training curves, temporal data |
| `box_plot` | Distributions | Performance across groups |
| `heatmap` | Correlations/matrices | Feature correlations |
| `scatter` | Relationships | Two continuous variables |

## Implementation

When executing this skill, Claude Code should:

1. **Read paper_spec.yaml** to get figure specifications
2. **Load experiment data** (CSV files, etc.)
3. **Generate each figure** using matplotlib/seaborn

### Example: ROC Curve

```python
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.metrics import roc_curve, auc

# Style settings
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12

# Load data from all folds
dfs = []
for fold in range(3):
    df = pd.read_csv(f'results_{fold}_test.csv')
    df['fold'] = fold
    dfs.append(df)
df = pd.concat(dfs)

# Create figure
fig, ax = plt.subplots(figsize=(6, 6), dpi=300)

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

# Plot each fold
for fold in range(3):
    fold_df = df[df['fold'] == fold].dropna(subset=['pred_prob', 'label'])
    fpr, tpr, _ = roc_curve(fold_df['label'], fold_df['pred_prob'])
    roc_auc = auc(fpr, tpr)
    ax.plot(fpr, tpr, color=colors[fold], lw=2,
            label=f'Fold {fold} (AUC = {roc_auc:.3f})')

# Plot overall
df_clean = df.dropna(subset=['pred_prob', 'label'])
fpr_all, tpr_all, _ = roc_curve(df_clean['label'], df_clean['pred_prob'])
roc_auc_all = auc(fpr_all, tpr_all)
ax.plot(fpr_all, tpr_all, color=colors[3], lw=2.5, linestyle='--',
        label=f'Overall (AUC = {roc_auc_all:.3f})')

# Reference line
ax.plot([0, 1], [0, 1], 'k--', lw=1, alpha=0.5)

ax.set_xlim([0.0, 1.0])
ax.set_ylim([0.0, 1.05])
ax.set_xlabel('False Positive Rate (1 - Specificity)')
ax.set_ylabel('True Positive Rate (Sensitivity)')
ax.set_title('ROC Curves')
ax.legend(loc='lower right')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('figures/fig_roc.png', dpi=300, bbox_inches='tight')
plt.close()
```

### Example: Institution Bar Chart

```python
fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

# Sort by AUC descending
results = sorted(results, key=lambda x: x['auc'], reverse=True)
institutions = [r['institution'] for r in results]
aucs = [r['auc'] for r in results]

# Create bar chart
colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(results)))
bars = ax.barh(range(len(institutions)), aucs, color=colors)

# Add labels
for i, (bar, auc_val, n) in enumerate(zip(bars, aucs, ns)):
    ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
            f'{auc_val:.3f} (n={n:,})', va='center', fontsize=9)

ax.set_xlabel('AUC-ROC')
ax.set_title('Model Performance by Institution')
ax.axvline(x=overall_auc, color='red', linestyle='--', label='Overall AUC')

plt.savefig('figures/fig_institution.png', dpi=300, bbox_inches='tight')
```

### Example: Confusion Matrix

```python
from sklearn.metrics import confusion_matrix

cm = confusion_matrix(y_true, y_pred)

fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
im = ax.imshow(cm, cmap=plt.cm.Blues)
cbar = ax.figure.colorbar(im, ax=ax, shrink=0.8)

# Labels
classes = ['Negative', 'Positive']
ax.set_xticks([0, 1])
ax.set_yticks([0, 1])
ax.set_xticklabels(classes)
ax.set_yticklabels(classes)
ax.set_xlabel('Predicted')
ax.set_ylabel('True')

# Annotations
for i in range(2):
    for j in range(2):
        text = f'{cm[i, j]:,}\n({cm[i, j]/cm.sum()*100:.1f}%)'
        ax.text(j, i, text, ha='center', va='center',
               color='white' if cm[i, j] > cm.max()/2 else 'black')

plt.savefig('figures/fig_confusion.png', dpi=300, bbox_inches='tight')
```

## Style Guidelines

### General
- Use 300 DPI for publication quality
- Use `bbox_inches='tight'` to avoid cropping
- Use consistent color schemes across figures
- Include proper axis labels and titles
- Add legends where appropriate
- Use grid lines sparingly (alpha=0.3)

### Colors
```python
# Recommended color palettes
colors_categorical = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
colors_sequential = plt.cm.Blues(np.linspace(0.4, 0.9, n))
```

### Fonts
```python
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.labelsize'] = 11
```

### Figure Sizes
| Type | Size (inches) |
|------|---------------|
| Single column | (4, 4) to (6, 6) |
| Wide/overview | (10, 6) to (12, 8) |
| Bar chart | (8, 5) |

## Notes

- For architecture diagrams, use `/paper-diagrams` instead
- Run `/paper-qa` after generating figures to verify quality
- Ensure numbers in figures match the paper text
