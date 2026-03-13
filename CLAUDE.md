# PaperForge - AI Agent Instructions

This file tells Claude Code / Codex / AI agents how to use PaperForge
to auto-generate academic papers from experiment directories.

## What is PaperForge?

A CLI tool that scans an experiment directory (data files, images, logs, docs),
feeds everything to Azure OpenAI, and produces a bilingual (EN/JA) academic paper as PDF.

## Installation

```bash
pip install git+https://github.com/pphouse/paper-forge.git
# Or with doc extraction support (Word/PDF):
pip install "paper-forge[all] @ git+https://github.com/pphouse/paper-forge.git"
```

### System requirements for PDF build

```bash
# XeLaTeX + Japanese fonts (required for PDF output)
sudo apt-get install -y texlive-xetex texlive-fonts-recommended texlive-lang-japanese fonts-ipaexfont
```

## Primary Command: `paper-forge forge`

This is the main command. Run it from or pointed at an experiment directory.

```bash
# Minimal - just point at the experiment dir
paper-forge forge /path/to/experiment/

# With extra documents for context
paper-forge forge /path/to/experiment/ --doc report.docx --doc notes.pdf

# Full options
paper-forge forge /path/to/experiment/ \
    --title-en "Effect of X on Y" \
    --title-ja "XがYに与える影響" \
    --author "Alice Smith" --affiliation "MIT" \
    --template twocol \
    --overview "We studied the effect of X on Y using method Z..."
```

### What `forge` does automatically:

1. Scans the experiment directory recursively
2. Finds and categorizes: CSV/JSON/YAML data, images (PNG/JPG), documents (MD/TXT/logs), code files
3. Analyzes all data files (column stats, suggested figure types)
4. Extracts text from Word (.docx), PDF (.pdf), Markdown (.md) files
5. Copies images to the paper project as potential figures
6. Sends all collected context to Azure OpenAI GPT to draft the paper
7. Generates Mermaid diagrams and renders to PNG
8. Builds bilingual PDF (English + Japanese) via XeLaTeX

### Output

By default, output goes to `{experiment_dir}_paper/`:
```
experiment_paper/
  paper_spec.yaml    # Generated paper spec (editable)
  output/
    paper_en.pdf     # English PDF
    paper_ja.pdf     # Japanese PDF
  figures/            # Auto-generated diagrams + copied images
```

### Key Options

| Option | Description |
|--------|-------------|
| `-o, --project-dir` | Custom output directory |
| `--doc FILE` | Add external document for context (repeatable) |
| `--overview TEXT` | Research overview (auto-derived if omitted) |
| `--title-en TEXT` | English title (auto-derived if omitted) |
| `--title-ja TEXT` | Japanese title (auto-derived if omitted) |
| `--template` | `twocol`, `onecol`, `nature`, `ieee` |
| `--author TEXT` | Author name (repeatable) |
| `--affiliation TEXT` | Affiliation matching author order |
| `--lang` | `en`, `ja`, or `both` (default: both) |
| `--no-build` | Generate spec only, skip PDF build |

## Environment Variables

```bash
# Required for AI generation
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"  # or your deployment name
```

## Other Useful Commands

```bash
# Build/rebuild PDF from existing spec
paper-forge build ./experiment_paper/ --lang all

# Check project status
paper-forge status ./experiment_paper/

# Analyze a single data file
paper-forge analyze ./data/results.csv

# Launch web editor for manual editing
paper-forge edit ./experiment_paper/ --host 0.0.0.0 --port 5000
```

## Python API

```python
from paper_forge.pipeline import Pipeline

pipeline = Pipeline("./output_paper")
spec = pipeline.forge(
    experiment_dir="./my_experiment",
    extra_docs=["report.docx", "notes.pdf"],
    title_en="My Paper Title",
)
```

## Typical AI Agent Workflow

When a user says "write a paper from this experiment data":

1. Check if paper-forge is installed: `pip show paper-forge`
2. If not, install it: `pip install git+https://github.com/pphouse/paper-forge.git`
3. Check Azure OpenAI env vars are set
4. Run: `paper-forge forge . --title-en "..." --author "..."`
5. The PDF will be in `../*_paper/output/`

## File Types Recognized

| Category | Extensions |
|----------|-----------|
| Data | `.csv`, `.json`, `.yaml`, `.yml`, `.tsv`, `.xlsx` |
| Images | `.png`, `.jpg`, `.jpeg`, `.svg`, `.tiff`, `.bmp`, `.gif` |
| Documents | `.md`, `.txt`, `.rst`, `.log`, `.tex`, `.docx`, `.pdf`, `.pptx` |
| Code | `.py`, `.r`, `.jl`, `.m`, `.ipynb` |
