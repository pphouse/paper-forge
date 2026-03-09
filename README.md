# PaperForge

Research data to academic paper PDF generator with interactive editing.

Supports **English** and **Japanese** bilingual output.

## Features

- **Bilingual PDF output** - Generate publication-quality PDFs in English and Japanese from a single spec
- **Interactive web editor** - Split-pane editor with live preview, Ctrl+S save, Ctrl+B build
- **Multiple templates** - Two-column, one-column, Nature-style, IEEE-style
- **Markdown content** - Write paper sections in Markdown with table, math, and footnote support
- **Figure generation** - Programmatic figure creation with colorblind-safe palettes
- **YAML-based spec** - Human-readable, editable paper specification format
- **CLI + Library + Web** - Use as command-line tool, Python library, or web app

## Quick Start

### Install

```bash
cd paper-forge
pip install -e .
```

### Create a new paper project

```bash
paper-forge init my-paper \
  --title-en "My Research Paper" \
  --title-ja "私の研究論文" \
  --template twocol \
  --author "Jane Doe" --affiliation "MIT"
```

### Edit the paper

Edit `my-paper/paper_spec.yaml` directly, or launch the web editor:

```bash
paper-forge edit my-paper
# Opens http://127.0.0.1:5000
```

### Build PDFs

```bash
paper-forge build my-paper --lang all
# Generates: my-paper/output/paper_en.pdf, paper_ja.pdf
```

## Web Editor

The web editor provides a split-pane interface:

- **Left pane**: Tabbed editor for metadata, abstract, sections, references, figures
- **Right pane**: Live HTML preview of the paper
- **Language toggle**: Switch between EN/JA editing and preview
- **Keyboard shortcuts**: Ctrl+S (save), Ctrl+B (build PDF)
- **Auto-save**: Saves automatically after 3 seconds of inactivity

Launch with:

```bash
paper-forge edit /path/to/projects --port 5000
```

## Paper Specification Format

Papers are defined in `paper_spec.yaml` with bilingual support:

```yaml
meta:
  title:
    en: "Paper Title"
    ja: "論文タイトル"
  template: twocol  # twocol, onecol, nature, ieee

authors:
  - name: "Author Name"
    affiliation: "University"

abstract:
  en: |
    English abstract in Markdown...
  ja: |
    日本語の要旨...

sections:
  - heading:
      en: "Introduction"
      ja: "はじめに"
    content:
      en: |
        Section content in **Markdown**.

        | Col1 | Col2 |
        |------|------|
        | A    | B    |
      ja: |
        **Markdown**で書かれたセクション内容。

references:
  - key: smith2024
    authors: "J. Smith et al."
    title: "Paper Title"
    journal: "Nature, 612, 100-110"
    year: 2024
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `paper-forge init <dir>` | Create new paper project |
| `paper-forge build <dir>` | Build PDF(s) |
| `paper-forge edit <dir>` | Launch web editor |
| `paper-forge preview <dir>` | Generate HTML preview |
| `paper-forge analyze <file>` | Analyze research data |
| `paper-forge status <dir>` | Show project status |
| `paper-forge figures <dir>` | Generate figures |

## Python API

```python
from paper_forge.pipeline import Pipeline

pipeline = Pipeline("my-paper")
pipeline.init_project(
    title_en="My Paper",
    title_ja="私の論文",
    template="twocol"
)

# Build PDFs
results = pipeline.build_all()
# {'en': '/path/to/paper_en.pdf', 'ja': '/path/to/paper_ja.pdf'}
```

## Templates

| Template | Style | Use Case |
|----------|-------|----------|
| `twocol` | Two-column, Times, booktabs | General journals |
| `onecol` | One-column, wide margins | Preprints, theses |
| `nature` | Nature/Science style | High-impact journals |
| `ieee` | IEEE conference format | CS conferences |

## Requirements

- Python 3.10+
- WeasyPrint (auto-installed)
- System fonts for Japanese (e.g., Noto Sans CJK JP, WenQuanYi)

## License

MIT
