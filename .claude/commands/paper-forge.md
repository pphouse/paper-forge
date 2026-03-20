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
4. **Build** - Compile PDF (English & Japanese)

## Workflow

This skill orchestrates the full paper generation pipeline:

```
experiment_dir/          project_dir/output/
├── results.csv    -->   ├── Paper_en.pdf
├── metrics.json         └── Paper_ja.pdf
└── notes.md
```

## Steps

### Step 1: Analyze
```
/paper-analyze <experiment_dir>
```

### Step 2: Generate Content
```
/paper-generate <experiment_dir> --output <project_dir>
```

### Step 3: Create Figures
```
/paper-figures <project_dir>
```

### Step 4: Build PDF
```
/paper-build <project_dir> --lang all
```

## Alternative: CLI Command

You can also use the paperclaw CLI directly:

```bash
paperclaw forge ./experiments/ \
    --title-en "My Paper Title" \
    --author "Author Name"
```

## Output Structure

```
experiment_dir_paper/
├── paper_spec.yaml      # Editable paper specification
├── figures/             # Generated figures
│   ├── fig_roc.png
│   └── fig_performance.png
└── output/
    ├── Paper_en.pdf     # English PDF
    └── Paper_ja.pdf     # Japanese PDF
```

## Tips

- Run individual skills (`/paper-analyze`, `/paper-figures`) for debugging
- Edit `paper_spec.yaml` manually to refine content
- Re-run `/paper-build` after manual edits
