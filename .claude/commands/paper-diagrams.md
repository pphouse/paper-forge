# Paper Diagrams

Generate architecture and workflow diagrams using draw.io (diagrams.net) format.

## Usage

```
/paper-diagrams <project_dir> [--type architecture|workflow|pipeline]
```

## What This Does

1. Analyzes the model/system architecture from code or description
2. Generates a draw.io XML file (`.drawio`)
3. Exports to PNG/SVG for paper inclusion
4. Saves to `<project_dir>/figures/`

## Why draw.io?

- **Professional quality**: Publication-ready diagrams
- **Editable**: Users can modify the `.drawio` file
- **Cross-platform**: Works on any OS
- **Free**: No license required
- **Export formats**: PNG, SVG, PDF at any resolution

## Diagram Types

### 1. Model Architecture
For neural network / ML model architectures:

```
Input Layer → Encoder → Fusion → Classifier → Output
```

### 2. Workflow/Pipeline
For data processing workflows:

```
Data Collection → Preprocessing → Training → Evaluation → Deployment
```

### 3. System Architecture
For multi-component systems:

```
┌─────────────┐     ┌─────────────┐
│  Component A │ ←→ │  Component B │
└─────────────┘     └─────────────┘
```

## Implementation

When executing this skill, Claude Code should:

1. **Identify architecture components** from:
   - Model code (PyTorch, TensorFlow)
   - Config files
   - User description

2. **Generate draw.io XML** with proper styling

3. **Export to PNG** using draw.io CLI or API

### draw.io XML Structure

```xml
<mxfile>
  <diagram name="Architecture">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <!-- ECG Encoder Box -->
        <mxCell id="ecg_encoder" value="ECG Encoder&#xa;(CNN)"
                style="rounded=1;whiteSpace=wrap;html=1;fillColor=#4ECDC4;strokeColor=#333333;fontStyle=1"
                vertex="1" parent="1">
          <mxGeometry x="40" y="120" width="120" height="80" as="geometry"/>
        </mxCell>

        <!-- X-ray Encoder Box -->
        <mxCell id="xray_encoder" value="X-ray Encoder&#xa;(ResNet)"
                style="rounded=1;whiteSpace=wrap;html=1;fillColor=#45B7D1;strokeColor=#333333;fontStyle=1"
                vertex="1" parent="1">
          <mxGeometry x="40" y="240" width="120" height="80" as="geometry"/>
        </mxCell>

        <!-- Fusion Layer -->
        <mxCell id="fusion" value="Feature&#xa;Fusion"
                style="rounded=1;whiteSpace=wrap;html=1;fillColor=#96CEB4;strokeColor=#333333;fontStyle=1"
                vertex="1" parent="1">
          <mxGeometry x="240" y="160" width="100" height="100" as="geometry"/>
        </mxCell>

        <!-- Classifier -->
        <mxCell id="classifier" value="Classifier&#xa;(FC Layers)"
                style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFEAA7;strokeColor=#333333;fontStyle=1"
                vertex="1" parent="1">
          <mxGeometry x="420" y="175" width="120" height="70" as="geometry"/>
        </mxCell>

        <!-- Arrows -->
        <mxCell id="arrow1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2"
                edge="1" parent="1" source="ecg_encoder" target="fusion">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="arrow2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2"
                edge="1" parent="1" source="xray_encoder" target="fusion">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <mxCell id="arrow3" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2"
                edge="1" parent="1" source="fusion" target="classifier">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Color Palette

Use consistent, professional colors:

| Component Type | Color Code | Name |
|---------------|------------|------|
| Input/Data | `#4ECDC4` | Teal |
| Encoder/Feature | `#45B7D1` | Blue |
| Fusion/Processing | `#96CEB4` | Green |
| Output/Classifier | `#FFEAA7` | Yellow |
| Attention/Important | `#FF6B6B` | Red |
| Background | `#F8F9FA` | Light Gray |

### Style Guidelines

```xml
<!-- Box style -->
style="rounded=1;whiteSpace=wrap;html=1;fillColor=#COLOR;strokeColor=#333333;fontStyle=1;fontSize=12"

<!-- Arrow style -->
style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic"

<!-- Text style -->
style="text;html=1;align=center;verticalAlign=middle;fontSize=11"
```

## Export Options

### Option 1: draw.io CLI (Recommended)

```bash
# Install draw.io CLI
npm install -g @diagrams/cli

# Export to PNG
drawio-export -f png -o figures/fig_architecture.png diagrams/architecture.drawio

# Export at high resolution
drawio-export -f png -s 2 -o figures/fig_architecture.png diagrams/architecture.drawio
```

### Option 2: draw.io Desktop

1. Open the `.drawio` file in draw.io desktop app
2. File → Export as → PNG
3. Set scale to 200-300% for high resolution
4. Save to `figures/`

### Option 3: Python with diagrams library

For simpler diagrams, use Python's `diagrams` library:

```python
from diagrams import Diagram, Cluster, Edge
from diagrams.custom import Custom

with Diagram("Model Architecture", show=False, filename="figures/fig_architecture",
             outformat="png", graph_attr={"dpi": "300"}):

    with Cluster("Input"):
        ecg = Custom("ECG", "./icons/ecg.png")
        xray = Custom("X-ray", "./icons/xray.png")

    with Cluster("Encoders"):
        ecg_enc = Custom("CNN", "./icons/cnn.png")
        xray_enc = Custom("ResNet", "./icons/resnet.png")

    fusion = Custom("Fusion", "./icons/fusion.png")
    classifier = Custom("Classifier", "./icons/fc.png")
    output = Custom("AS Prediction", "./icons/output.png")

    ecg >> ecg_enc >> fusion
    xray >> xray_enc >> fusion
    fusion >> classifier >> output
```

## Template: Multimodal Architecture

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="2026-03-21">
  <diagram name="Multimodal Architecture" id="architecture">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100" pageHeight="850" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <!-- Title -->
        <mxCell id="title" value="Multimodal Deep Learning Architecture" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontSize=16;fontStyle=1" vertex="1" parent="1">
          <mxGeometry x="350" y="20" width="400" height="30" as="geometry"/>
        </mxCell>

        <!-- Input Labels -->
        <mxCell id="ecg_label" value="ECG&#xa;Waveform" style="text;html=1;align=right;verticalAlign=middle;fontSize=10" vertex="1" parent="1">
          <mxGeometry x="0" y="135" width="60" height="40" as="geometry"/>
        </mxCell>

        <mxCell id="xray_label" value="Chest&#xa;Radiograph" style="text;html=1;align=right;verticalAlign=middle;fontSize=10" vertex="1" parent="1">
          <mxGeometry x="0" y="255" width="60" height="40" as="geometry"/>
        </mxCell>

        <!-- ECG Branch -->
        <mxCell id="ecg_enc" value="ECG Encoder&#xa;(1D-CNN)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#4ECDC4;strokeColor=#2C3E50;fontStyle=1;fontSize=11" vertex="1" parent="1">
          <mxGeometry x="80" y="120" width="140" height="70" as="geometry"/>
        </mxCell>

        <!-- X-ray Branch -->
        <mxCell id="xray_enc" value="Image Encoder&#xa;(ResNet-50)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#45B7D1;strokeColor=#2C3E50;fontStyle=1;fontSize=11" vertex="1" parent="1">
          <mxGeometry x="80" y="240" width="140" height="70" as="geometry"/>
        </mxCell>

        <!-- Feature boxes -->
        <mxCell id="ecg_feat" value="ECG&#xa;Features" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E8E8E8;strokeColor=#999999;fontSize=9;fontStyle=2" vertex="1" parent="1">
          <mxGeometry x="260" y="135" width="60" height="40" as="geometry"/>
        </mxCell>

        <mxCell id="xray_feat" value="Image&#xa;Features" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E8E8E8;strokeColor=#999999;fontSize=9;fontStyle=2" vertex="1" parent="1">
          <mxGeometry x="260" y="255" width="60" height="40" as="geometry"/>
        </mxCell>

        <!-- Fusion -->
        <mxCell id="fusion" value="Feature&#xa;Fusion" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#96CEB4;strokeColor=#2C3E50;fontStyle=1;fontSize=12" vertex="1" parent="1">
          <mxGeometry x="380" y="170" width="100" height="90" as="geometry"/>
        </mxCell>

        <!-- Classifier -->
        <mxCell id="classifier" value="Classifier&#xa;(FC Layers)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFEAA7;strokeColor=#2C3E50;fontStyle=1;fontSize=11" vertex="1" parent="1">
          <mxGeometry x="540" y="185" width="120" height="60" as="geometry"/>
        </mxCell>

        <!-- Output -->
        <mxCell id="output" value="AS&#xa;Prediction" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FF6B6B;strokeColor=#2C3E50;fontStyle=1;fontSize=11;fontColor=#FFFFFF" vertex="1" parent="1">
          <mxGeometry x="720" y="185" width="80" height="60" as="geometry"/>
        </mxCell>

        <!-- Arrows -->
        <mxCell id="arr1" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic" edge="1" parent="1" source="ecg_enc" target="ecg_feat">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr2" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic" edge="1" parent="1" source="xray_enc" target="xray_feat">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr3" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic" edge="1" parent="1" source="ecg_feat" target="fusion">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr4" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic" edge="1" parent="1" source="xray_feat" target="fusion">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr5" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic" edge="1" parent="1" source="fusion" target="classifier">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr6" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;strokeWidth=2;endArrow=classic" edge="1" parent="1" source="classifier" target="output">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

## Workflow

1. Run `/paper-diagrams <project_dir>` to generate `.drawio` file
2. Open in draw.io to review/edit if needed
3. Export to PNG at 300 DPI
4. Save to `figures/fig_overview.png`

## Notes

- draw.io files are XML and can be version controlled
- Users can edit diagrams without regenerating
- For data-driven figures (ROC, bar charts), use `/paper-figures` instead
- Keep diagrams simple and focused - one concept per diagram
