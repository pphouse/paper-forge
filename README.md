# PaperClaw

**Experiment directory -> Academic paper PDF, fully automated.**

Point PaperClaw at your experiment results directory. It scans data files, images, logs, and documents, then uses Claude Code to draft a complete bilingual (English / Japanese) academic paper and build publication-quality PDFs.

## Quick Start

```bash
# Install
pip install git+https://github.com/pphouse/paper-forge.git

# Generate paper from experiment directory (uses Claude Code)
paperclaw forge ./my_experiment/
```

That's it. Output lands in `./my_experiment_paper/output/`.

## Branches

| Branch | Backend | Use Case |
|--------|---------|----------|
| `main` | Claude Code CLI | Default - no API keys needed |
| `azure-openai` | Azure OpenAI API | Production / batch processing |

## What It Does

```
experiment_dir/                    paper_project/output/
├── results/                       ├── paper_en.pdf    <- English PDF
│   ├── accuracy.csv     ------>   ├── paper_ja.pdf    <- Japanese PDF
│   └── metrics.json               └── ...
├── plots/
│   └── fig1.png
├── README.md
└── notes.txt
```

1. **Scans** the experiment directory recursively (CSV, JSON, YAML, images, code, logs)
2. **Analyzes** data files (statistics, column types, suggested visualizations)
3. **Extracts** text from documents (Word, PDF, Markdown, PowerPoint)
4. **Generates** a complete paper draft via Claude Code (Abstract -> Conclusion)
5. **Creates** figures using matplotlib/seaborn
6. **Builds** bilingual PDF with proper academic formatting

## Installation

```bash
# Basic install
pip install git+https://github.com/pphouse/paper-forge.git

# With document extraction (Word/PDF/PowerPoint support)
pip install "paperclaw[docs] @ git+https://github.com/pphouse/paper-forge.git"
```

## Usage

### `paperclaw forge` - The Main Command

```bash
# Minimal: just point at experiment dir
paperclaw forge ./experiments/

# Add external documents for context
paperclaw forge ./experiments/ --doc report.docx --doc literature_review.pdf

# Full options
paperclaw forge ./experiments/ \
    --title-en "Comparative Analysis of Deep Learning Methods" \
    --title-ja "深層学習手法の比較分析" \
    --author "Alice Smith" --affiliation "MIT" \
    --template ieee \
    -o ./my_paper/
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --project-dir DIR` | Output directory (default: `{experiment_dir}_paper`) |
| `--doc FILE` | Extra document for context (repeatable) |
| `--overview TEXT` | Research overview (auto-derived if omitted) |
| `--title-en TEXT` | English title (auto-derived if omitted) |
| `--title-ja TEXT` | Japanese title |
| `--template STYLE` | `twocol` (default), `onecol`, `nature`, `ieee` |
| `--author NAME` | Author name (repeatable) |
| `--affiliation AFF` | Affiliation matching author order |
| `--lang LANG` | `en`, `ja`, or `both` (default) |
| `--no-build` | Generate paper spec only, skip PDF |

### Other Commands

```bash
paperclaw build ./paper_project/ --lang all    # Rebuild PDFs
paperclaw status ./paper_project/              # Show project status
paperclaw analyze ./data/results.csv           # Analyze a data file
paperclaw preview ./paper_project/ --lang en   # HTML preview
```

## Claude Code Skills

PaperClaw provides skills for step-by-step paper generation:

| Skill | Description |
|-------|-------------|
| `/paper-forge` | Full automated pipeline |
| `/paper-analyze` | Scan and analyze experiment data |
| `/paper-generate` | Generate paper_spec.yaml content |
| `/paper-figures` | Create data visualizations (ROC, bar charts, etc.) |
| `/paper-diagrams` | Create architecture diagrams (draw.io format) |
| `/paper-qa` | QA check with OCR (figure-text consistency) |
| `/paper-build` | Build PDF from spec |

### Recommended Workflow

```
/paper-analyze ./experiment/
/paper-generate ./experiment/ --output ./paper/
/paper-figures ./paper/
/paper-diagrams ./paper/      # Optional: architecture diagrams
/paper-qa ./paper/            # Quality check before build
/paper-build ./paper/
```

To use skills, copy `.claude/commands/` to your project.

## Python API

```python
from paperclaw.pipeline import Pipeline

# Full auto from experiment directory
pipeline = Pipeline("./output_paper")
spec = pipeline.forge(
    experiment_dir="./my_experiment",
    extra_docs=["report.docx"],
    title_en="My Paper",
    authors=[{"name": "Alice", "affiliation": "MIT"}],
)
```

## File Types Recognized

| Category | Extensions | What happens |
|----------|-----------|-------------|
| Data | `.csv`, `.json`, `.yaml`, `.tsv`, `.xlsx` | Auto-analyzed (stats, column types) |
| Images | `.png`, `.jpg`, `.svg`, `.tiff`, `.gif` | Copied as paper figures |
| Documents | `.md`, `.txt`, `.log`, `.tex` | Text extracted for context |
| Rich docs | `.docx`, `.pdf`, `.pptx` | Text extracted (requires `[docs]` extra) |
| Code | `.py`, `.r`, `.jl`, `.m`, `.ipynb` | Listed for context |

## Templates

| Template | Style | Use Case |
|----------|-------|----------|
| `twocol` | Two-column, Times, booktabs | General journals |
| `onecol` | One-column, wide margins | Preprints, theses |
| `nature` | Nature/Science style | High-impact journals |
| `ieee` | IEEE conference format | CS conferences |

## Output Structure

```
my_experiment_paper/
├── paper_spec.yaml          # Editable paper specification
├── data/                    # Copied/analyzed data
├── figures/                 # Images + generated diagrams
│   ├── fig1.png
│   └── fig_roc.png
└── output/
    ├── paper_en.pdf         # English PDF
    └── paper_ja.pdf         # Japanese PDF
```

## License

MIT
