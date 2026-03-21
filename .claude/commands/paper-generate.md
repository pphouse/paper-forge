# Paper Generate

Generate paper content (paper_spec.yaml) from experiment data using Claude Code.

## Usage

```
/paper-generate <experiment_dir> [--output <project_dir>] [--title "Paper Title"]
```

## What This Does

1. Uses the data analysis from `/paper-analyze`
2. Generates a complete bilingual paper specification:
   - Abstract (English & Japanese)
   - Introduction with background and objectives
   - Methods (study design, data, model, analysis)
   - Results with specific metrics
   - Discussion with interpretation
   - Conclusion
   - Tables and figure specifications
   - References

3. Saves to `paper_spec.yaml` in the project directory

## Workflow

When executing this skill, Claude Code should:

1. **First run `/paper-analyze`** to understand the experiment data
2. **Create project directory structure**
   ```bash
   mkdir -p <project_dir>/{figures,output,data}
   ```
3. **Ask user for context** (if needed):
   - Research question/hypothesis
   - Target journal/format
   - Any specific requirements
4. **Generate paper_spec.yaml** with bilingual content
5. **Use current date** - Check today's date for the publication year

## paper_spec.yaml Structure

```yaml
meta:
  title:
    en: "Paper Title in English"
    ja: "日本語の論文タイトル"
  template: twocol  # twocol, onecol, nature, ieee
  date: "2026"  # Use current year

authors:
  - name: "Author Name"
    affiliation: "Institution"
    email: "email@example.com"

keywords:
  en: "keyword1, keyword2, keyword3"
  ja: "キーワード1, キーワード2, キーワード3"

abstract:
  en: |
    Background: ...
    Methods: ...
    Results: ...
    Conclusions: ...
  ja: |
    背景：...
    方法：...
    結果：...
    結論：...

sections:
  - heading:
      en: "Introduction"
      ja: "はじめに"
    content:
      en: |
        Paragraph 1...

        Paragraph 2...
      ja: |
        段落1...

        段落2...
    figures: [fig_overview]  # Reference figures in this section

  - heading:
      en: "Methods"
      ja: "方法"
    content:
      en: ""
      ja: ""
    subsections:
      - heading:
          en: "Study Design"
          ja: "研究デザイン"
        content:
          en: "..."
          ja: "..."

  - heading:
      en: "Results"
      ja: "結果"
    content:
      en: "..."
      ja: "..."
    figures: [fig_roc, fig_institution]
    tables: [tab_performance]

  - heading:
      en: "Discussion"
      ja: "考察"
    content:
      en: "..."
      ja: "..."

  - heading:
      en: "Conclusion"
      ja: "結論"
    content:
      en: "..."
      ja: "..."

figures:
  fig_overview:
    path: "figures/fig_overview.png"
    caption:
      en: "Overview of the proposed method..."
      ja: "提案手法の概要..."
    label: "fig:overview"
    wide: true  # For two-column layout: span both columns

  fig_roc:
    path: "figures/fig_roc.png"
    caption:
      en: "ROC curves showing model performance..."
      ja: "モデル性能を示すROC曲線..."
    label: "fig:roc"
    wide: false

tables:
  tab_performance:
    caption:
      en: "Model performance metrics"
      ja: "モデル性能指標"
    label: "tab:performance"
    columns: ["Metric", "Value"]
    data:
      - ["AUC-ROC", "0.857"]
      - ["Accuracy", "93.2%"]
    # IMPORTANT: Keep tables concise (max 6-8 rows)
    # Split large tables into multiple smaller tables

references:
  - key: "author2024"
    authors: "Author A, Author B"
    title: "Paper title"
    journal: "Journal Name"
    year: 2024
    doi: "10.1000/example"

acknowledgments:
  en: "This work was supported by..."
  ja: "本研究は...の支援を受けた。"
```

## Writing Guidelines

### Content Quality
- **Be specific**: Include actual numbers from the analysis
- **Be balanced**: Discuss both strengths and limitations
- **Be concise**: Academic writing should be precise

### Bilingual Content
- Generate BOTH English and Japanese for ALL text fields
- Japanese should be natural academic Japanese (学術的な日本語)
- Avoid machine translation artifacts
- Use appropriate technical terms in Japanese

### Table Layout Tips
- **Keep tables concise**: Maximum 6-8 rows per table
- **Split large tables**: If more rows needed, create multiple tables
- **Use subsections**: Place related tables in different sections
- **Avoid wide tables**: Prefer vertical layout over horizontal
- This prevents layout overflow issues in PDF

### Figure References
- Reference figures using the `figures:` list in sections
- Use `wide: true` for overview/architecture diagrams
- Place figures close to their first reference in text

## Notes

- Generate BOTH English and Japanese for all text fields
- Use the current year (check date) for publication date
- Keep tables small to avoid PDF layout issues
- Reference actual metrics from `/paper-analyze` output
