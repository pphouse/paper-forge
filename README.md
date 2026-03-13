# PaperForge

**Experiment directory → Academic paper PDF, fully automated.**

Point PaperForge at your experiment results directory. It scans data files, images, logs, and documents, then uses AI (Azure OpenAI) to draft a complete bilingual (English / Japanese) academic paper and build publication-quality PDFs via XeLaTeX.

Designed to be invoked by AI coding agents (Claude Code, Codex, etc.) or used directly from the command line.

## Quick Start

```bash
# Install
pip install git+https://github.com/your-user/paper-forge.git

# Set Azure OpenAI credentials
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"

# Generate paper from experiment directory
paper-forge forge ./my_experiment/
```

That's it. Output lands in `./my_experiment_paper/output/`.

## What It Does

```
experiment_dir/                    paper_project/output/
├── results/                       ├── paper_en.pdf    ← English PDF
│   ├── accuracy.csv     ──────►   ├── paper_ja.pdf    ← Japanese PDF
│   └── metrics.json               └── ...
├── plots/
│   └── fig1.png
├── README.md
└── notes.txt
```

1. **Scans** the experiment directory recursively (CSV, JSON, YAML, images, code, logs)
2. **Analyzes** data files (statistics, column types, suggested visualizations)
3. **Extracts** text from documents (Word, PDF, Markdown, PowerPoint)
4. **Generates** a complete paper draft via Azure OpenAI (Abstract → Conclusion)
5. **Creates** Mermaid diagrams (method pipeline, architecture, etc.) and renders to PNG
6. **Builds** bilingual PDF via XeLaTeX with proper academic formatting

## Installation

```bash
# Basic install
pip install git+https://github.com/your-user/paper-forge.git

# With document extraction (Word/PDF/PowerPoint support)
pip install "paper-forge[docs] @ git+https://github.com/your-user/paper-forge.git"

# Full install (AI + docs + dev tools)
pip install "paper-forge[all] @ git+https://github.com/your-user/paper-forge.git"
```

### System Dependencies (for PDF build)

```bash
# Ubuntu/Debian
sudo apt-get install -y texlive-xetex texlive-fonts-recommended \
    texlive-lang-japanese fonts-ipaexfont

# macOS
brew install --cask mactex
```

## Usage

### `paper-forge forge` — The Main Command

```bash
# Minimal: just point at experiment dir
paper-forge forge ./experiments/

# Add external documents for context
paper-forge forge ./experiments/ --doc report.docx --doc literature_review.pdf

# Full options
paper-forge forge ./experiments/ \
    --title-en "Comparative Analysis of Deep Learning Methods" \
    --title-ja "深層学習手法の比較分析" \
    --author "Alice Smith" --affiliation "MIT" \
    --author "Bob Jones" --affiliation "Stanford" \
    --template ieee \
    -o ./my_paper/
```

### Options

| Option | Description |
|--------|-------------|
| `-o, --project-dir DIR` | Output directory (default: `{experiment_dir}_paper`) |
| `--doc FILE` | Extra document for context — repeatable (`.docx`, `.pdf`, `.md`) |
| `--overview TEXT` | Research overview (auto-derived from experiment data if omitted) |
| `--title-en TEXT` | English title (auto-derived if omitted) |
| `--title-ja TEXT` | Japanese title |
| `--template STYLE` | `twocol` (default), `onecol`, `nature`, `ieee` |
| `--author NAME` | Author name (repeatable) |
| `--affiliation AFF` | Affiliation matching author order |
| `--lang LANG` | `en`, `ja`, or `both` (default) |
| `--no-build` | Generate paper spec only, skip PDF |

### Other Commands

```bash
paper-forge build ./paper_project/ --lang all    # Rebuild PDFs
paper-forge status ./paper_project/              # Show project status
paper-forge analyze ./data/results.csv           # Analyze a data file
paper-forge edit ./paper_project/ --port 5000    # Web editor
```

## For AI Agents (Claude Code, Codex)

See [`CLAUDE.md`](./CLAUDE.md) for detailed agent instructions.

Typical workflow:
```
User: "この実験結果から論文を書いて"
Agent: pip install paper-forge → paper-forge forge . → PDF ready
```

PaperForge is designed to work as a tool that AI agents call. The `CLAUDE.md` file contains structured instructions so agents know exactly how to use every command.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Yes (for AI generation) | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | Yes | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Yes | Model deployment name |

## Python API

```python
from paper_forge.pipeline import Pipeline

# Full auto from experiment directory
pipeline = Pipeline("./output_paper")
spec = pipeline.forge(
    experiment_dir="./my_experiment",
    extra_docs=["report.docx"],
    title_en="My Paper",
    authors=[{"name": "Alice", "affiliation": "MIT"}],
)

# Or step by step
pipeline = Pipeline("./output_paper")
pipeline.init_project(title_en="My Paper", template="twocol")
analysis = pipeline.analyze_data("./data/results.csv")
pdf_path = pipeline.build_pdf("en")
```

## File Types Recognized

| Category | Extensions | What happens |
|----------|-----------|-------------|
| Data | `.csv`, `.json`, `.yaml`, `.tsv`, `.xlsx` | Auto-analyzed (stats, column types) |
| Images | `.png`, `.jpg`, `.svg`, `.tiff`, `.gif` | Copied as paper figures |
| Documents | `.md`, `.txt`, `.log`, `.tex` | Text extracted for AI context |
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
│   ├── fig1.mmd             # Mermaid source
│   └── copied_image.png
└── output/
    ├── paper_en.pdf         # English PDF
    └── paper_ja.pdf         # Japanese PDF
```

## License

MIT
