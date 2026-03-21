# Paper Diagrams

Generate architecture and workflow diagrams, export to PNG, and integrate into paper.

## Usage

```
/paper-diagrams <project_dir> [--type architecture|workflow|pipeline]
```

## What This Does

1. Analyzes the model/system architecture
2. Generates diagram source file (draw.io XML or Python)
3. **Exports to PNG** (300 DPI, publication quality)
4. **Updates paper_spec.yaml** to include the figure
5. Saves to `<project_dir>/figures/`

## Complete Workflow

When executing this skill, Claude Code should:

### Step 1: Create diagrams directory
```bash
mkdir -p <project_dir>/diagrams
```

### Step 2: Generate diagram using Python (Recommended)

Use matplotlib for reliable PNG export without external dependencies:

```python
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

def create_architecture_diagram(output_path, title="Model Architecture"):
    """Create a publication-quality architecture diagram."""
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')

    # Colors
    colors = {
        'input': '#E8F5E9',
        'encoder_ecg': '#4ECDC4',
        'encoder_img': '#45B7D1',
        'fusion': '#96CEB4',
        'classifier': '#FFEAA7',
        'output': '#FF6B6B',
        'feature': '#ECEFF1'
    }

    def add_box(ax, x, y, w, h, text, color, fontsize=10, fontweight='bold'):
        box = FancyBboxPatch((x, y), w, h,
                             boxstyle="round,pad=0.02,rounding_size=0.1",
                             facecolor=color, edgecolor='#2C3E50', linewidth=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center',
                fontsize=fontsize, fontweight=fontweight, wrap=True)

    def add_arrow(ax, start, end):
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', lw=2, color='#2C3E50'))

    # Title
    ax.text(6, 6.5, title, ha='center', va='center',
            fontsize=14, fontweight='bold')

    # Input boxes
    add_box(ax, 0.5, 4, 1.5, 1, 'ECG\nWaveform', colors['input'], 9)
    add_box(ax, 0.5, 2, 1.5, 1, 'Chest\nX-ray', colors['input'], 9)

    # Encoders
    add_box(ax, 2.5, 3.8, 2, 1.4, 'ECG Encoder\n(1D-CNN)', colors['encoder_ecg'])
    add_box(ax, 2.5, 1.8, 2, 1.4, 'Image Encoder\n(ResNet)', colors['encoder_img'])

    # Features
    add_box(ax, 5, 4, 1.2, 0.8, 'ECG\nFeatures', colors['feature'], 8, 'normal')
    add_box(ax, 5, 2.2, 1.2, 0.8, 'Image\nFeatures', colors['feature'], 8, 'normal')

    # Fusion
    add_box(ax, 6.8, 2.8, 1.8, 1.4, 'Feature\nFusion', colors['fusion'])

    # Classifier
    add_box(ax, 9.2, 2.9, 1.6, 1.2, 'Classifier\n(FC)', colors['classifier'])

    # Output
    circle = plt.Circle((11.5, 3.5), 0.5, color=colors['output'], ec='#2C3E50', lw=2)
    ax.add_patch(circle)
    ax.text(11.5, 3.5, 'AS\nProb', ha='center', va='center',
            fontsize=9, fontweight='bold', color='white')

    # Arrows
    add_arrow(ax, (2, 4.5), (2.5, 4.5))
    add_arrow(ax, (2, 2.5), (2.5, 2.5))
    add_arrow(ax, (4.5, 4.5), (5, 4.4))
    add_arrow(ax, (4.5, 2.5), (5, 2.6))
    add_arrow(ax, (6.2, 4.2), (6.8, 3.8))
    add_arrow(ax, (6.2, 2.8), (6.8, 3.2))
    add_arrow(ax, (8.6, 3.5), (9.2, 3.5))
    add_arrow(ax, (10.8, 3.5), (11, 3.5))

    # Info boxes at bottom
    info_y = 0.3
    add_box(ax, 0.5, info_y, 3, 1.2,
            'Training\n3-fold CV, lr=3e-5\nBatch=32, Adam',
            '#FFF3E0', 8, 'normal')
    add_box(ax, 4, info_y, 3, 1.2,
            'Dataset\nTrain: 2.16M\nTest: 12,423',
            '#E8EAF6', 8, 'normal')
    add_box(ax, 7.5, info_y, 3, 1.2,
            'Results\nAUC: 0.857\nSpec: 99.5%',
            '#E8F5E9', 8, 'normal')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Saved: {output_path}")

# Generate
create_architecture_diagram("figures/fig_overview.png",
                           "Multimodal Deep Learning Architecture")
```

### Step 3: Also save draw.io source (for manual editing)

```python
drawio_template = '''<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net">
  <diagram name="Architecture">
    <!-- Draw.io XML content here -->
  </diagram>
</mxfile>
'''

with open("diagrams/architecture.drawio", "w") as f:
    f.write(drawio_template)
```

### Step 4: Update paper_spec.yaml

```python
import yaml

# Load existing spec
with open("paper_spec.yaml", "r") as f:
    spec = yaml.safe_load(f)

# Add or update figure
if "figures" not in spec:
    spec["figures"] = {}

spec["figures"]["fig_overview"] = {
    "path": "figures/fig_overview.png",
    "caption": {
        "en": "Overview of the multimodal deep learning architecture for AS prediction.",
        "ja": "AS予測のためのマルチモーダル深層学習アーキテクチャの概要。"
    },
    "label": "fig:overview",
    "wide": True
}

# Ensure figure is referenced in Introduction
for section in spec.get("sections", []):
    if section.get("heading", {}).get("en") == "Introduction":
        if "figures" not in section:
            section["figures"] = []
        if "fig_overview" not in section["figures"]:
            section["figures"].append("fig_overview")
        break

# Save
with open("paper_spec.yaml", "w") as f:
    yaml.dump(spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("Updated paper_spec.yaml with fig_overview")
```

## Alternative: draw.io CLI Export

If draw.io desktop or CLI is available:

```bash
# Check if draw.io CLI is available
which drawio || which draw.io

# Export using draw.io CLI (macOS)
/Applications/draw.io.app/Contents/MacOS/draw.io \
    --export --format png --scale 2 \
    --output figures/fig_overview.png \
    diagrams/architecture.drawio

# Or using npm drawio-export
npx @diagrams/cli export -f png -s 2 \
    -o figures/fig_overview.png \
    diagrams/architecture.drawio
```

## Diagram Templates

### Template 1: Multimodal Architecture (ML)

```python
# For multimodal deep learning models
components = [
    {"name": "Input A", "type": "input"},
    {"name": "Encoder A", "type": "encoder"},
    {"name": "Input B", "type": "input"},
    {"name": "Encoder B", "type": "encoder"},
    {"name": "Fusion", "type": "fusion"},
    {"name": "Classifier", "type": "classifier"},
    {"name": "Output", "type": "output"}
]
```

### Template 2: Data Pipeline

```python
# For data processing workflows
components = [
    {"name": "Raw Data", "type": "input"},
    {"name": "Preprocessing", "type": "process"},
    {"name": "Feature Engineering", "type": "process"},
    {"name": "Model Training", "type": "model"},
    {"name": "Evaluation", "type": "output"}
]
```

### Template 3: System Architecture

```python
# For multi-component systems
components = [
    {"name": "Frontend", "type": "client"},
    {"name": "API Gateway", "type": "gateway"},
    {"name": "Service A", "type": "service"},
    {"name": "Service B", "type": "service"},
    {"name": "Database", "type": "storage"}
]
```

## Full Implementation Script

```python
#!/usr/bin/env python
"""Generate architecture diagram and integrate into paper."""

import os
import yaml
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

PROJECT_DIR = "."  # Set to project directory

def create_multimodal_architecture(output_path):
    """Create multimodal architecture diagram."""
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis('off')

    # [Full implementation as shown above]
    # ...

    plt.savefig(output_path, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    return output_path

def update_paper_spec(spec_path, figure_id, figure_info):
    """Update paper_spec.yaml with new figure."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f)

    if 'figures' not in spec:
        spec['figures'] = {}

    spec['figures'][figure_id] = figure_info

    with open(spec_path, 'w', encoding='utf-8') as f:
        yaml.dump(spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return spec

def main():
    os.makedirs(f"{PROJECT_DIR}/figures", exist_ok=True)
    os.makedirs(f"{PROJECT_DIR}/diagrams", exist_ok=True)

    # 1. Generate diagram
    output_path = f"{PROJECT_DIR}/figures/fig_overview.png"
    create_multimodal_architecture(output_path)
    print(f"Generated: {output_path}")

    # 2. Update paper_spec.yaml
    figure_info = {
        "path": "figures/fig_overview.png",
        "caption": {
            "en": "Overview of the multimodal deep learning architecture.",
            "ja": "マルチモーダル深層学習アーキテクチャの概要。"
        },
        "label": "fig:overview",
        "wide": True
    }
    update_paper_spec(f"{PROJECT_DIR}/paper_spec.yaml", "fig_overview", figure_info)
    print("Updated paper_spec.yaml")

    print("\nDone! Run /paper-build to include in PDF.")

if __name__ == "__main__":
    main()
```

## Style Guidelines

### Colors (Consistent Palette)
| Component | Color | Hex |
|-----------|-------|-----|
| Input/Data | Light Green | `#E8F5E9` |
| ECG Encoder | Teal | `#4ECDC4` |
| Image Encoder | Blue | `#45B7D1` |
| Fusion | Green | `#96CEB4` |
| Classifier | Yellow | `#FFEAA7` |
| Output | Red | `#FF6B6B` |
| Feature/Intermediate | Light Gray | `#ECEFF1` |

### Figure Specifications
- **DPI**: 300 (publication quality)
- **Size**: 12x7 inches for wide figures
- **Format**: PNG with white background
- **Font**: Sans-serif, 10-12pt

## Workflow Integration

```
/paper-analyze ./experiment/
/paper-generate ./experiment/ --output ./paper/
/paper-figures ./paper/
/paper-diagrams ./paper/     # <-- Generate + export + integrate
/paper-qa ./paper/
/paper-build ./paper/
```

## Output

After running `/paper-diagrams`:

```
project_dir/
├── diagrams/
│   └── architecture.drawio    # Editable source
├── figures/
│   └── fig_overview.png       # Exported PNG (300 DPI)
└── paper_spec.yaml            # Updated with figure reference
```

## Notes

- Python/matplotlib method is preferred (no external dependencies)
- draw.io XML is saved for manual editing if needed
- Figure is automatically added to paper_spec.yaml
- Run `/paper-build` after to include in final PDF
