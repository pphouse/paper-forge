# CardioPaperClaw

**AI-driven Academic Paper Writing Agent for Cardiovascular Research**

CardioPaperClaw is an AI-powered tool that automates the generation of academic papers from experimental data. Developed as part of SIP Phase 3 "Integrated Healthcare System Construction" WG-4 (Clinical Support Solutions Development), it enables rapid transformation of AI model evaluation results into publication-ready manuscripts.

## Overview

```
experiment_results/                 output/
├── results_fold0.csv              ├── paper_en.pdf    <- English manuscript
├── results_fold1.csv    ------>   ├── paper_ja.pdf    <- Japanese manuscript
├── results_fold2.csv              └── figures/
└── config.yaml                        ├── fig_roc.png
                                       ├── fig_confusion.png
                                       └── fig_institution.png
```

**Key Features:**
- Generates IMRaD-format academic papers from experimental data
- Bilingual output (English / Japanese)
- Publication-quality figures (ROC curves, confusion matrices, performance charts)
- In-text citations with `\cite{}` and bibliography
- CLIDAS research group style compliance

## Quick Start

```bash
# Install
pip install git+https://github.com/pphouse/CardioPaperClaw.git

# Generate paper from experiment directory
paperclaw forge ./experiment_results/
```

Output appears in `./experiment_results_paper/output/`.

## Use Case: Cardiovascular AI Model Papers

This tool was designed specifically for publishing cardiovascular AI research, such as:

| Model Type | Input Modalities | Example Output |
|------------|------------------|----------------|
| AS Prediction | ECG + Chest X-ray | Multimodal deep learning paper |
| AF Detection | ECG | Single-modality screening paper |
| HFpEF Prediction | ECG + CXR + Echo | Multi-modal fusion paper |
| Valvular Disease | Chest X-ray | Image-based detection paper |

### Example: AS Prediction Model

```bash
# Analyze experimental results
/paper-analyze ./major3_AS_results/

# Generate paper content
/paper-generate ./major3_AS_results/ --output ./AS_paper/

# Create publication-quality figures
/paper-figures ./AS_paper/

# Build bilingual PDF
/paper-build ./AS_paper/ --lang all
```

**Generated in ~16 minutes:**
- 4-page manuscript (EN/JA)
- ROC curves with fold-wise performance
- Confusion matrix with counts and percentages
- Institution-wise performance comparison
- Properly formatted references

## Pipeline Architecture

CardioPaperClaw uses a 6-agent pipeline:

```
┌─────────────────────────────────────────────────────────────┐
│                  CardioPaperClaw Pipeline                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [Experimental Data]                                       │
│          │                                                  │
│          ▼                                                  │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│   │ Analyze  │───▶│Literature│───▶│ Figures  │             │
│   │ Agent 1  │    │ Agent 2  │    │ Agent 3  │             │
│   └──────────┘    └──────────┘    └──────────┘             │
│          │              │              │                    │
│          └──────────────┴──────────────┘                    │
│                         │                                   │
│                         ▼                                   │
│                  ┌──────────┐                               │
│                  │ Generate │                               │
│                  │ Agent 4  │                               │
│                  └──────────┘                               │
│                         │                                   │
│                         ▼                                   │
│   ┌──────────┐    ┌──────────┐                             │
│   │  Review  │───▶│  Build   │                             │
│   │ Agent 5  │    │ Agent 6  │                             │
│   └──────────┘    └──────────┘                             │
│                         │                                   │
│                         ▼                                   │
│              [paper_en.pdf, paper_ja.pdf]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Claude Code Skills

Available skills for step-by-step paper generation:

| Skill | Description |
|-------|-------------|
| `/paper-forge` | Full automated pipeline |
| `/paper-analyze` | Analyze experimental data (AUC, CI, metrics) |
| `/paper-literature` | Search and organize related work |
| `/paper-figures` | Generate ROC, confusion matrix, bar charts |
| `/paper-generate` | Generate LaTeX content (EN/JA) |
| `/paper-review` | Quality check (consistency, completeness) |
| `/paper-build` | Compile to PDF (pdflatex/XeLaTeX) |

### Recommended Workflow

```bash
# 1. Analyze experimental data
/paper-analyze ./experiment/

# 2. Search related literature
/paper-literature ./paper_project/

# 3. Generate figures
/paper-figures ./paper_project/

# 4. Generate paper content
/paper-generate ./paper_project/

# 5. Quality check
/paper-review ./paper_project/

# 6. Build PDF
/paper-build ./paper_project/ --lang all
```

## Figure Style (CLIDAS Standard)

All figures follow CLIDAS research group standards:

```python
# ROC curve colors
ROC_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

# Institution/bar charts
colors = plt.cm.Blues(np.linspace(0.4, 0.9, n))

# Confusion matrix
cmap = plt.cm.Blues

# Grid styling
ax.grid(True, alpha=0.3)
```

**Output specifications:**
- Resolution: 300 DPI
- Format: PNG (manuscript), TIFF (submission)
- Font: DejaVu Sans
- Size: Optimized for column width (~89mm)

## Citation Format

In-text citations using `\cite{}`:

```latex
% In text
Aortic stenosis affects 2--7\% of adults \cite{otto2021}.
Deep learning models have shown promising results \cite{cohen2021,kwon2020}.

% References section
\begin{thebibliography}{9}
\bibitem{otto2021}
Otto CM, et al. 2020 ACC/AHA Guideline... \textit{Circulation}. 2021.
\end{thebibliography}
```

## Installation

```bash
# Basic install
pip install git+https://github.com/pphouse/CardioPaperClaw.git

# With document extraction support (Word/PDF)
pip install "paperclaw[docs] @ git+https://github.com/pphouse/CardioPaperClaw.git"
```

### Requirements

- Python 3.9+
- LaTeX distribution (pdflatex, xelatex)
- Japanese fonts (Hiragino Mincho ProN for macOS)

## Output Structure

```
paper_project/
├── paper_en.tex              # English LaTeX source
├── paper_ja.tex              # Japanese LaTeX source
├── analysis_report.json      # Extracted metrics
├── figures/
│   ├── fig_roc.png           # ROC curves
│   ├── fig_confusion.png     # Confusion matrix
│   └── fig_institution.png   # Institution performance
├── literature/
│   └── references.md         # Related work summary
├── review_report.md          # QA results
└── output/
    ├── paper_en.pdf          # English PDF
    └── paper_ja.pdf          # Japanese PDF
```

## Performance

| Metric | Traditional | CardioPaperClaw | Improvement |
|--------|-------------|-----------------|-------------|
| Literature review | 1-2 weeks | ~4 min | 99.9% |
| Figure creation | 3-5 days | ~2 min | 99.9% |
| Manuscript writing | 2-4 weeks | ~5 min | 99.9% |
| Formatting | 2-3 days | ~1 min | 99.9% |
| **Total** | **1.5-3 months** | **~16 min** | **99.9%** |

## Acknowledgments

Developed as part of:
- **SIP Phase 3**: "Integrated Healthcare System Construction"
- **WG-4**: Clinical Support Solutions Development
- **Development Item 7**: Multimodal AI Research and Development
- **CLIDAS Research Group**: Clinical Data Science Consortium, Japan

## License

MIT
