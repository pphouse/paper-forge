# Paper Diagrams

Generate architecture and workflow diagrams using Graphviz, export to PNG, and integrate into paper.

## Usage

```
/paper-diagrams <project_dir> [--type architecture|workflow|pipeline]
```

## What This Does

1. Analyzes the model/system architecture
2. Generates diagram using **Graphviz** (Python `graphviz` package)
3. Exports to **PNG** (300 DPI, publication quality)
4. Saves source file (`.gv`) for manual editing
5. **Updates paper_spec.yaml** with figure reference

## Requirements

```bash
# Install Graphviz system package
brew install graphviz    # macOS
apt install graphviz     # Ubuntu

# Install Python package
pip install graphviz
```

## Implementation

When executing this skill, Claude Code should:

### Step 1: Create directories
```bash
mkdir -p <project_dir>/figures
```

### Step 2: Generate diagram with Graphviz

```python
#!/usr/bin/env python
"""Generate architecture diagram using Graphviz."""

from graphviz import Digraph
import yaml
import os

def create_multimodal_architecture(output_path, format='png'):
    """Create multimodal deep learning architecture diagram."""

    dot = Digraph(comment='Multimodal Architecture')
    dot.attr(rankdir='LR', size='12,8', dpi='300')
    dot.attr('node', shape='box', style='rounded,filled',
             fontname='Helvetica', fontsize='11')
    dot.attr('edge', fontname='Helvetica', fontsize='9')

    # Colors
    colors = {
        'input': '#E8F5E9',
        'encoder_ecg': '#4ECDC4',
        'encoder_img': '#45B7D1',
        'feature': '#ECEFF1',
        'fusion': '#96CEB4',
        'classifier': '#FFEAA7',
        'output': '#FF6B6B'
    }

    # Input cluster
    with dot.subgraph(name='cluster_input') as c:
        c.attr(label='Input', style='rounded', color='#CCCCCC')
        c.node('ecg_input', 'ECG Waveform\n(12-lead)', fillcolor=colors['input'])
        c.node('xray_input', 'Chest X-ray\n(PA view)', fillcolor=colors['input'])

    # Encoder cluster
    with dot.subgraph(name='cluster_encoder') as c:
        c.attr(label='Encoders', style='rounded', color='#CCCCCC')
        c.node('ecg_encoder', 'ECG Encoder\n(1D-CNN)', fillcolor=colors['encoder_ecg'])
        c.node('xray_encoder', 'Image Encoder\n(ResNet-50)', fillcolor=colors['encoder_img'])

    # Feature cluster
    with dot.subgraph(name='cluster_features') as c:
        c.attr(label='Features', style='rounded', color='#CCCCCC')
        c.node('ecg_feat', 'ECG Features\n(512-d)', fillcolor=colors['feature'])
        c.node('xray_feat', 'Image Features\n(512-d)', fillcolor=colors['feature'])

    # Fusion and output
    dot.node('fusion', 'Feature Fusion\n(Concatenation)', fillcolor=colors['fusion'])
    dot.node('combined', 'Combined\n(1024-d)', fillcolor=colors['feature'])
    dot.node('classifier', 'Classifier\n(FC Layers)', fillcolor=colors['classifier'])
    dot.node('output', 'AS Prediction\n(Probability)', fillcolor=colors['output'],
             fontcolor='white')

    # Edges
    dot.edge('ecg_input', 'ecg_encoder')
    dot.edge('xray_input', 'xray_encoder')
    dot.edge('ecg_encoder', 'ecg_feat')
    dot.edge('xray_encoder', 'xray_feat')
    dot.edge('ecg_feat', 'fusion')
    dot.edge('xray_feat', 'fusion')
    dot.edge('fusion', 'combined')
    dot.edge('combined', 'classifier')
    dot.edge('classifier', 'output')

    # Info cluster
    with dot.subgraph(name='cluster_info') as c:
        c.attr(rank='sink', style='rounded', color='#CCCCCC', label='Configuration')
        c.node('info_train', 'Training\n3-fold CV\nlr=3e-5, batch=32',
               fillcolor='#FFF3E0', shape='note')
        c.node('info_data', 'Dataset\nTrain: 2.16M\nTest: 12,423',
               fillcolor='#E8EAF6', shape='note')
        c.node('info_result', 'Results\nAUC: 0.857\nSpec: 99.5%',
               fillcolor='#E8F5E9', shape='note')
        c.edge('info_train', 'info_data', style='invis')
        c.edge('info_data', 'info_result', style='invis')

    # Render
    output_base = output_path.replace('.png', '').replace('.pdf', '')
    dot.render(output_base, format=format, cleanup=True)
    dot.save(f"{output_base}.gv")

    print(f"Generated: {output_base}.{format}")
    print(f"Source: {output_base}.gv")
    return f"{output_base}.{format}"


def update_paper_spec(spec_path, figure_id, figure_info):
    """Update paper_spec.yaml with figure reference."""
    with open(spec_path, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f)

    if 'figures' not in spec:
        spec['figures'] = {}

    spec['figures'][figure_id] = figure_info

    # Add to Introduction if not present
    for section in spec.get('sections', []):
        if section.get('heading', {}).get('en') == 'Introduction':
            if 'figures' not in section:
                section['figures'] = []
            if figure_id not in section['figures']:
                section['figures'].append(figure_id)
            break

    with open(spec_path, 'w', encoding='utf-8') as f:
        yaml.dump(spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"Updated: {spec_path}")


def main(project_dir):
    os.makedirs(f"{project_dir}/figures", exist_ok=True)

    # Generate diagram
    output = create_multimodal_architecture(f"{project_dir}/figures/fig_overview")

    # Update paper_spec.yaml
    figure_info = {
        'path': 'figures/fig_overview.png',
        'caption': {
            'en': 'Overview of the multimodal deep learning architecture for AS prediction.',
            'ja': 'AS予測のためのマルチモーダル深層学習アーキテクチャの概要。'
        },
        'label': 'fig:overview',
        'wide': True
    }
    update_paper_spec(f"{project_dir}/paper_spec.yaml", 'fig_overview', figure_info)

    print("\nDone! Run /paper-build to include in PDF.")


if __name__ == "__main__":
    import sys
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    main(project_dir)
```

### Step 3: Run the script

```bash
python generate_architecture.py <project_dir>
```

## Diagram Templates

### Template 1: Multimodal Architecture (ML)

```python
def create_multimodal_diagram(dot, inputs, encoders, fusion_name, output_name):
    """Generic multimodal architecture."""
    for inp, enc in zip(inputs, encoders):
        dot.node(inp['id'], inp['label'], fillcolor=inp['color'])
        dot.node(enc['id'], enc['label'], fillcolor=enc['color'])
        dot.edge(inp['id'], enc['id'])
        dot.edge(enc['id'], 'fusion')

    dot.node('fusion', fusion_name, fillcolor='#96CEB4')
    dot.node('output', output_name, fillcolor='#FF6B6B', fontcolor='white')
    dot.edge('fusion', 'output')
```

### Template 2: Data Pipeline

```python
def create_pipeline_diagram(dot, stages):
    """Sequential pipeline diagram."""
    dot.attr(rankdir='TB')  # Top to bottom

    for i, stage in enumerate(stages):
        dot.node(f's{i}', stage['label'], fillcolor=stage['color'])
        if i > 0:
            dot.edge(f's{i-1}', f's{i}')
```

### Template 3: CNN Architecture (PlotNeuralNet style)

```python
def create_cnn_diagram(dot, layers):
    """CNN layer diagram."""
    prev = None
    for i, layer in enumerate(layers):
        node_id = f'layer{i}'
        label = f"{layer['name']}\n{layer['shape']}"
        dot.node(node_id, label, fillcolor=layer['color'], shape='box3d')
        if prev:
            dot.edge(prev, node_id)
        prev = node_id
```

## Color Palette

| Component | Color | Hex |
|-----------|-------|-----|
| Input | Light Green | `#E8F5E9` |
| Encoder (ECG) | Teal | `#4ECDC4` |
| Encoder (Image) | Blue | `#45B7D1` |
| Features | Light Gray | `#ECEFF1` |
| Fusion | Green | `#96CEB4` |
| Classifier | Yellow | `#FFEAA7` |
| Output | Red | `#FF6B6B` |
| Training Info | Orange | `#FFF3E0` |
| Data Info | Indigo | `#E8EAF6` |

## Graphviz Quick Reference

### Node Shapes
- `box` - Rectangle (default)
- `box3d` - 3D box (for CNN layers)
- `ellipse` - Oval
- `diamond` - Decision
- `note` - Note/info box
- `cylinder` - Database

### Graph Directions
- `rankdir='LR'` - Left to Right
- `rankdir='TB'` - Top to Bottom
- `rankdir='BT'` - Bottom to Top
- `rankdir='RL'` - Right to Left

### Subgraph (Clusters)
```python
with dot.subgraph(name='cluster_name') as c:
    c.attr(label='Label', style='rounded', color='#CCCCCC')
    c.node('node1', 'Node 1')
    c.node('node2', 'Node 2')
```

### Edge Styles
```python
dot.edge('a', 'b', style='dashed')   # Dashed
dot.edge('a', 'b', style='bold')     # Bold
dot.edge('a', 'b', style='invis')    # Invisible (for alignment)
dot.edge('a', 'b', label='label')    # With label
```

## Output Files

```
project_dir/
├── figures/
│   ├── fig_overview.png   # PNG (300 DPI)
│   └── fig_overview.gv    # Graphviz source (editable)
└── paper_spec.yaml        # Updated with figure reference
```

## Workflow

```
/paper-analyze ./experiment/
/paper-generate ./experiment/ --output ./paper/
/paper-figures ./paper/
/paper-diagrams ./paper/     # <-- Graphviz diagram
/paper-qa ./paper/
/paper-build ./paper/
```

## Editing Diagrams

The `.gv` file can be edited and re-rendered:

```bash
# Edit the source
vim figures/fig_overview.gv

# Re-render
dot -Tpng -Gdpi=300 figures/fig_overview.gv -o figures/fig_overview.png
```

Or use online editors:
- https://dreampuf.github.io/GraphvizOnline/
- VS Code extension: "Graphviz Preview"

## Why Graphviz?

| Feature | Graphviz | matplotlib | draw.io |
|---------|----------|------------|---------|
| Dependencies | Light | Heavy | External app |
| Editable source | `.gv` (text) | Python code | `.drawio` XML |
| Auto-layout | Yes | Manual | Manual |
| PNG export | Built-in | Built-in | Requires CLI |
| CLI friendly | Yes | Yes | Limited |

## Notes

- Graphviz automatically handles node layout
- Source files (`.gv`) are plain text and git-friendly
- Can also export to SVG, PDF formats
- Use `dpi='300'` for publication quality
