# PaperClaw - Claude Code Instructions

This file tells Claude Code how to use PaperClaw to auto-generate academic papers from experiment directories.

## What is PaperClaw?

A CLI tool that scans an experiment directory (data files, images, logs, docs), uses Claude Code to generate content, and produces a bilingual (EN/JA) academic paper as PDF.

## Installation

```bash
pip install git+https://github.com/pphouse/paper-forge.git

# With doc extraction support (Word/PDF):
pip install "paperclaw[docs] @ git+https://github.com/pphouse/paper-forge.git"
```

## Skills (Step-by-Step Workflow)

PaperClaw provides skills in `.claude/commands/` for granular control:

| Skill | Description |
|-------|-------------|
| `/paper-forge` | Full automated pipeline |
| `/paper-analyze` | Scan and analyze experiment data |
| `/paper-generate` | Generate paper_spec.yaml content |
| `/paper-figures` | Create data visualizations |
| `/paper-qa` | QA check with OCR (figure-text consistency) |
| `/paper-build` | Build PDF from spec |

### Recommended Workflow

1. **Analyze** - Understand the experiment data
   ```
   /paper-analyze ./experiment_dir/
   ```

2. **Generate** - Create paper content (you generate this directly)
   ```
   /paper-generate ./experiment_dir/ --output ./paper_project/
   ```

3. **Figures** - Generate visualizations from data
   ```
   /paper-figures ./paper_project/
   ```

4. **QA Check** - OCR-based quality assurance
   ```
   /paper-qa ./paper_project/
   ```
   - 図中の数値・ラベルをOCRで抽出
   - 本文との整合性チェック
   - 問題があれば修正して再実行

5. **Build** - Compile to PDF
   ```
   /paper-build ./paper_project/ --lang all
   ```

## CLI Commands

### `paperclaw forge` - Full Auto

```bash
paperclaw forge /path/to/experiment/ \
    --title-en "Effect of X on Y" \
    --title-ja "XがYに与える影響" \
    --author "Alice Smith" --affiliation "MIT"
```

### What `forge` does:

1. Scans the experiment directory recursively
2. Finds and categorizes: CSV/JSON/YAML data, images (PNG/JPG), documents (MD/TXT/logs)
3. Analyzes all data files (column stats, suggested figure types)
4. Extracts text from Word (.docx), PDF (.pdf), Markdown (.md) files
5. Sends all collected context to Claude Code to draft the paper
6. Generates matplotlib figures from data
7. Builds bilingual PDF via WeasyPrint

### Output

```
experiment_paper/
  paper_spec.yaml    # Generated paper spec (editable)
  figures/           # Generated figures
  output/
    paper_en.pdf     # English PDF
    paper_ja.pdf     # Japanese PDF
```

### Key Options

| Option | Description |
|--------|-------------|
| `-o, --project-dir` | Custom output directory |
| `--doc FILE` | Add external document for context (repeatable) |
| `--overview TEXT` | Research overview (auto-derived if omitted) |
| `--title-en TEXT` | English title (auto-derived if omitted) |
| `--title-ja TEXT` | Japanese title |
| `--template` | `twocol`, `onecol`, `nature`, `ieee` |
| `--no-build` | Generate spec only, skip PDF build |

## Other Commands

```bash
# Build/rebuild PDF from existing spec
paperclaw build ./experiment_paper/ --lang all

# Check project status
paperclaw status ./experiment_paper/

# Analyze a single data file
paperclaw analyze ./data/results.csv

# HTML preview
paperclaw preview ./experiment_paper/ --lang en
```

## Python API

```python
from paperclaw.pipeline import Pipeline

pipeline = Pipeline("./output_paper")
spec = pipeline.forge(
    experiment_dir="./my_experiment",
    extra_docs=["report.docx", "notes.pdf"],
    title_en="My Paper Title",
)
```

## Typical Workflow

When a user says "write a paper from this experiment data":

1. Install paperclaw if needed: `pip install git+https://github.com/pphouse/paper-forge.git`
2. Analyze the experiment data: `/paper-analyze ./experiment/`
3. Generate paper content: Write `paper_spec.yaml` with bilingual content
4. Create figures: Use matplotlib to generate figures from data
5. Build PDF: `paperclaw build ./paper_project/ --lang all`

## File Types Recognized

| Category | Extensions |
|----------|-----------|
| Data | `.csv`, `.json`, `.yaml`, `.yml`, `.tsv`, `.xlsx` |
| Images | `.png`, `.jpg`, `.jpeg`, `.svg`, `.tiff`, `.bmp`, `.gif` |
| Documents | `.md`, `.txt`, `.rst`, `.log`, `.tex`, `.docx`, `.pdf`, `.pptx` |
| Code | `.py`, `.r`, `.jl`, `.m`, `.ipynb` |

## paper_spec.yaml Format

```yaml
meta:
  title:
    en: "Paper Title"
    ja: "論文タイトル"
  template: twocol

abstract:
  en: "..."
  ja: "..."

sections:
  - heading:
      en: "Introduction"
      ja: "はじめに"
    content:
      en: "..."
      ja: "..."
    figures: [fig_1]
    tables: [tab_1]

figures:
  fig_1:
    path: "figures/fig_1.png"
    caption:
      en: "Figure caption"
      ja: "図のキャプション"
    label: "fig:example"

tables:
  tab_1:
    caption:
      en: "Table caption"
      ja: "表のキャプション"
    columns: ["Col1", "Col2"]
    data: [["val1", "val2"]]
```
