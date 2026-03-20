# Paper QA

Quality assurance check for generated papers using OCR and consistency analysis.

## Usage

```
/paper-qa <project_dir>
```

## What This Does

1. **Figure Quality Check**
   - Resolution and DPI validation
   - Text overlap detection
   - Axis label presence

2. **OCR Text Extraction**
   - Extract text from figures using pytesseract
   - Support for English + Japanese (`eng+jpn`)
   - Image preprocessing for better accuracy

3. **Consistency Check**
   - Compare numbers in figures vs paper text
   - Verify figure labels are mentioned in text
   - Check caption accuracy

4. **Feedback Generation**
   - List issues with severity levels
   - Provide improvement suggestions

## Requirements

```bash
# Install pytesseract
pip install pytesseract

# macOS
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

## Example Output

```
=== Figure QA Report ===

[fig_roc_curve]
  ✓ Resolution: 1800x1800 (OK)
  ✓ DPI: 300 (OK)
  ⚠ OCR detected numbers not in text: [0.857, 0.872, 0.866]
  → Suggestion: Add these values to Results section

[fig_performance]
  ✓ Resolution: 2400x1500 (OK)
  ⚠ No axis labels detected
  → Suggestion: Add xlabel/ylabel to figure

=== Consistency Issues ===
  - Figure 'fig_roc_curve' shows AUC=0.857, but text mentions 0.86
  - Label 'Specificity' in fig_roc_curve not mentioned in text

=== Summary ===
  Figures checked: 3
  Issues found: 4
  Errors: 0
  Warnings: 4
```

## Implementation

```python
from paperclaw.agents.figure_checker import FigureChecker
from paperclaw.models import PaperSpec
import yaml

# Load paper spec
with open("paper_spec.yaml") as f:
    spec = yaml.safe_load(f)

# Run QA check
checker = FigureChecker(use_ocr=True, language="eng+jpn")
report = checker.check_figures(spec, "./project_dir")

# Print results
for result in report.results:
    print(f"\n[{result.figure_id}]")
    print(f"  Path: {result.path}")
    print(f"  Resolution: {result.width}x{result.height}")
    print(f"  DPI: {result.dpi_estimate}")

    if result.extracted_text:
        print(f"  OCR text: {result.extracted_text[:100]}...")

    if result.detected_numbers:
        print(f"  Numbers found: {result.detected_numbers}")

    for issue in result.issues:
        print(f"  [{issue.severity}] {issue.message}")
        if issue.suggestion:
            print(f"    → {issue.suggestion}")

# Consistency issues
if report.number_consistency_issues:
    print("\n=== Number Consistency ===")
    for issue in report.number_consistency_issues:
        print(f"  - {issue['message']}")

# Get suggestions
suggestions = checker.suggest_improvements(report)
if suggestions:
    print("\n=== Suggestions ===")
    for s in suggestions:
        print(f"  - {s}")
```

## Workflow Integration

Run after `/paper-figures` and before final `/paper-build`:

```
/paper-analyze ./experiment/
/paper-generate ./experiment/ --output ./paper/
/paper-figures ./paper/
/paper-qa ./paper/          # <-- QA check here
/paper-build ./paper/
```

If issues found, fix figures or text, then re-run `/paper-qa`.

## Checks Performed

| Check | Severity | Description |
|-------|----------|-------------|
| File missing | Error | Figure file not found |
| Low resolution | Warning | Below 600x400 pixels |
| Low DPI | Warning | Below 150 DPI |
| Text at edge | Warning | Text may be cut off |
| No axis labels | Info | Common labels not detected |
| Numbers not in text | Info | Figure values not mentioned |
| Labels not in text | Info | Figure labels not explained |

## Tips

- Run with `--verbose` for detailed OCR output
- Use high-contrast figures for better OCR accuracy
- Ensure Japanese language pack is installed for bilingual papers
