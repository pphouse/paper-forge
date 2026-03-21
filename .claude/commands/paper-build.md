# Paper Build

Build PDF from paper_spec.yaml using paperclaw.

## Usage

```
/paper-build <project_dir> [--lang en|ja|all]
```

## What This Does

1. Reads `paper_spec.yaml` from the project directory
2. Validates all figure paths exist
3. Renders content using WeasyPrint (HTML/CSS based)
4. Generates publication-quality PDF(s)
5. Outputs to `<project_dir>/output/`

## Requirements

```bash
pip install /path/to/paper-forge
```

## Command

```bash
cd <project_dir>
paperclaw build . --lang all
```

## Output

```
project_dir/
  output/
    Paper_Title_en.pdf    # English version
    Paper_Title_ja.pdf    # Japanese version
```

## Templates

| Template | Description | Best For |
|----------|-------------|----------|
| `twocol` | Two-column, Times font | General journals |
| `onecol` | Single column, wide margins | Preprints, theses |
| `nature` | Nature/Science style | High-impact journals |
| `ieee` | IEEE conference format | CS conferences |

Set template in `paper_spec.yaml`:

```yaml
meta:
  template: twocol
```

## Layout Best Practices

### Avoiding Table/Text Overlap

Common issue: Tables overflow into adjacent text. Solutions:

1. **Keep tables small**: Max 6-8 rows per table
   ```yaml
   tables:
     tab_1:
       data:
         - ["Row1", "Val1"]
         - ["Row2", "Val2"]
         # ... max 6-8 rows
   ```

2. **Split large tables**: Break into multiple tables
   ```yaml
   tables:
     tab_demographics:
       caption: "Patient demographics"
       # First part of data

     tab_clinical:
       caption: "Clinical characteristics"
       # Second part of data
   ```

3. **Use narrow columns**: Prefer vertical over horizontal layout
   ```yaml
   columns: ["Metric", "Value"]  # Good - 2 columns
   # vs
   columns: ["A", "B", "C", "D", "E", "F"]  # Bad - too wide
   ```

4. **Place tables strategically**: Put in different sections
   ```yaml
   sections:
     - heading: "Methods"
       tables: [tab_demographics]  # Table 1 here

     - heading: "Results"
       tables: [tab_performance]   # Table 2 here
   ```

### Figure Placement

1. **Use `wide: true` for overview figures**
   ```yaml
   figures:
     fig_overview:
       wide: true  # Spans both columns
   ```

2. **Keep other figures single-column**
   ```yaml
   figures:
     fig_roc:
       wide: false  # Fits in one column
   ```

3. **Reference figures close to placement**
   - Place figure reference in the section where you discuss it

### Content Length

- **Abstract**: 150-300 words
- **Each section**: 300-800 words
- **Subsections**: 100-400 words

## Pre-build Checklist

Run these checks before building:

```bash
# 1. Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('paper_spec.yaml'))"

# 2. Check all figure files exist
for f in figures/*.png; do [ -f "$f" ] && echo "OK: $f" || echo "MISSING: $f"; done

# 3. Check image resolution
for f in figures/*.png; do
  identify "$f" 2>/dev/null | grep -oP '\d+x\d+' | head -1
done
```

## Troubleshooting

### PDF build fails

1. **YAML syntax error**
   ```bash
   python -c "import yaml; yaml.safe_load(open('paper_spec.yaml'))"
   ```

2. **Missing figure file**
   - Check paths in paper_spec.yaml match actual files

3. **Japanese font missing**
   - Install Japanese fonts: `brew install font-noto-sans-cjk-jp`

### Table overflow

1. Split table into smaller tables
2. Reduce column count
3. Shorten cell content

### Figure too large

1. Set `wide: false`
2. Reduce figure dimensions in matplotlib

## Preview Before PDF

Generate HTML preview first:

```bash
paperclaw preview <project_dir> --lang en --output preview.html
open preview.html  # Check layout in browser
```

## Post-build Review

After building PDF:

1. Check page breaks are sensible
2. Verify no text/table/figure overlap
3. Confirm all figures render correctly
4. Check Japanese text displays properly
5. Verify references are formatted correctly

## Quick Reference

```bash
# Build both languages
paperclaw build . --lang all

# Build English only
paperclaw build . --lang en

# Preview HTML
paperclaw preview . --lang en

# Check project status
paperclaw status .
```
