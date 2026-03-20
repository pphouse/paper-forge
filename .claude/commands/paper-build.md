# Paper Build

Build PDF from paper_spec.yaml using paperclaw.

## Usage

```
/paper-build <project_dir> [--lang en|ja|all]
```

## What This Does

1. Reads `paper_spec.yaml` from the project directory
2. Renders content using WeasyPrint (HTML/CSS based)
3. Generates publication-quality PDF(s)
4. Outputs to `<project_dir>/output/`

## Requirements

Make sure paperclaw is installed:

```bash
pip install /path/to/paper-forge
```

## Command

```bash
paperclaw build <project_dir> --lang all
```

## Output

```
project_dir/
  output/
    Paper_Title_en.pdf    # English version
    Paper_Title_ja.pdf    # Japanese version
```

## Templates

Available templates (set in paper_spec.yaml `meta.template`):

| Template | Description |
|----------|-------------|
| `twocol` | Two-column, Times font (default) |
| `onecol` | Single column, wide margins |
| `nature` | Nature/Science style |
| `ieee` | IEEE conference format |

## Troubleshooting

If PDF build fails:

1. Check that all figure paths in paper_spec.yaml exist
2. Verify Japanese fonts are available (for ja output)
3. Check for YAML syntax errors in paper_spec.yaml

## Preview (HTML)

To preview before building PDF:

```bash
paperclaw preview <project_dir> --lang en --output preview.html
```
