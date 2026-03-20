# Paper Generate

Generate paper content (paper_spec.yaml) from experiment data using Claude Code.

## Usage

```
/paper-generate <experiment_dir> [--output <project_dir>] [--title "Paper Title"]
```

## What This Does

1. Uses the data analysis from `/paper-analyze`
2. Generates a complete paper specification including:
   - Abstract (English & Japanese)
   - Introduction
   - Methods
   - Results
   - Discussion
   - Conclusion
   - Tables and figure specifications

3. Saves to `paper_spec.yaml` in the project directory

## Workflow

This skill generates the paper content. You (Claude Code) should:

1. First run `/paper-analyze` to understand the experiment data
2. Ask the user for any additional context (research goals, methods used)
3. Generate the paper_spec.yaml with bilingual content

## Output Format

The paper_spec.yaml follows this structure:

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
    figures: [fig_1, fig_2]
    tables: [tab_1]

figures:
  fig_1:
    path: "figures/fig_1.png"
    caption:
      en: "..."
      ja: "..."

tables:
  tab_1:
    caption:
      en: "..."
      ja: "..."
    columns: ["Col1", "Col2"]
    data: [["val1", "val2"]]
```

## Notes

- Generate BOTH English and Japanese for all text fields
- Japanese should be natural academic Japanese, not machine translation
- Reference actual data from the analysis in Results section
