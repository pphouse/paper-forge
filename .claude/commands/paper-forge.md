# Paper Forge

Full automated workflow: experiment directory -> academic paper PDF.

## Usage

```
/paper-forge <experiment_dir> [--title "Paper Title"] [--author "Author Name"]
```

## What This Does

Runs all paper generation steps in sequence:

1. **Analyze** - Scan and analyze experiment data
2. **Generate** - Create paper_spec.yaml with full content
3. **Figures** - Generate data visualizations
4. **Diagrams** - Create architecture diagrams (optional)
5. **QA** - Quality assurance check
6. **Build** - Compile PDF (English & Japanese)

## Workflow Diagram

```
experiment_dir/              project_dir/output/
├── results.csv        -->   ├── Paper_en.pdf
├── metrics.json             └── Paper_ja.pdf
└── notes.md
```

## Steps

### Step 1: Analyze Data
```
/paper-analyze <experiment_dir>
```
- Scans for CSV, JSON, images, code files
- Calculates statistics and metrics
- Identifies cross-validation folds
- Outputs analysis report

### Step 2: Generate Content
```
/paper-generate <experiment_dir> --output <project_dir>
```
- Creates project directory structure
- Generates paper_spec.yaml with bilingual content
- Defines figures and tables needed
- **Important**: Uses current year (2026) for date

### Step 3: Create Data Figures
```
/paper-figures <project_dir>
```
- ROC curves from classification results
- Bar charts for comparisons
- Confusion matrices
- Box plots for distributions

### Step 4: Create Architecture Diagrams (Optional)
```
/paper-diagrams <project_dir>
```
- Model architecture overview
- Generates PNG (300 DPI) using matplotlib
- Saves draw.io source for manual editing
- **Auto-updates paper_spec.yaml** with figure reference

### Step 5: QA Check
```
/paper-qa <project_dir>
```
- OCR extracts text/numbers from figures
- Compares with paper text for consistency
- Checks figure quality (resolution, DPI)
- Validates table layout (max 6-8 rows)
- Reports issues and recommendations

**If issues found**: Fix and re-run QA before building.

### Step 6: Build PDF
```
/paper-build <project_dir> --lang all
```
- Generates English and Japanese PDFs
- Uses WeasyPrint for rendering
- Outputs to `<project_dir>/output/`

## Output Structure

```
experiment_dir_paper/
├── paper_spec.yaml      # Editable paper specification
├── diagrams/            # draw.io source files
│   └── architecture.drawio
├── figures/             # Generated figures
│   ├── fig_overview.png
│   ├── fig_roc.png
│   ├── fig_institution.png
│   └── fig_confusion.png
└── output/
    ├── Paper_en.pdf     # English PDF
    └── Paper_ja.pdf     # Japanese PDF
```

## Alternative: CLI Command

```bash
paperclaw forge ./experiments/ \
    --title-en "My Paper Title" \
    --author "Author Name"
```

## Best Practices

### Tables
- Keep tables under 8 rows to prevent layout issues
- Split large tables into multiple smaller tables
- Place tables in different sections if needed

### Figures
- Use `wide: true` for overview/architecture diagrams
- Keep data figures (ROC, bar charts) single-column
- Export at 300 DPI

### Dates
- Always use the current year
- Today's date: Check `date` command

### Quality
- Always run `/paper-qa` before building
- Fix any warnings about table size
- Verify numbers in figures match text

## Troubleshooting

### Table overlaps text
1. Split table into smaller tables (max 6-8 rows each)
2. Reduce column count
3. Place tables in different sections

### Figure quality issues
1. Regenerate at 300 DPI
2. Check image dimensions

### Numbers don't match
1. Re-run `/paper-figures` with correct data
2. Update paper_spec.yaml text

## Tips

- Run individual skills for debugging: `/paper-analyze`, `/paper-figures`
- Edit `paper_spec.yaml` manually to refine content
- Re-run `/paper-build` after manual edits
- Use `/paper-diagrams` for professional architecture figures
