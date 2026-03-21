# Paper QA

Quality assurance check for generated papers using OCR and consistency analysis.

## Usage

```
/paper-qa <project_dir>
```

## What This Does

1. **Figure Quality Check**
   - Resolution validation (min 600x400)
   - DPI check (min 150 DPI, recommended 300)
   - File format validation

2. **OCR Text Extraction**
   - Extract text from figures using pytesseract
   - Support for English + Japanese (`eng+jpn`)
   - Preprocessing for better accuracy

3. **Consistency Check**
   - Compare numbers in figures vs paper text
   - Verify figure labels match text references
   - Check caption accuracy

4. **Layout Check**
   - Table size validation
   - Figure placement recommendations

5. **Feedback Generation**
   - Issues with severity levels (Error, Warning, Info)
   - Specific improvement suggestions

## Requirements

```bash
# Install pytesseract
pip install pytesseract Pillow

# macOS
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-jpn
```

## Implementation

When executing this skill, Claude Code should:

### 1. Check Figure Quality

```python
from PIL import Image
import os

def check_figure_quality(image_path):
    issues = []
    with Image.open(image_path) as img:
        width, height = img.size
        dpi = img.info.get('dpi', (72, 72))[0]

        # Resolution check
        if width < 600 or height < 400:
            issues.append(f"⚠ Low resolution: {width}x{height}")
        else:
            issues.append(f"✓ Resolution: {width}x{height} (OK)")

        # DPI check
        if dpi < 150:
            issues.append(f"⚠ Low DPI: {dpi} (recommend 300)")
        else:
            issues.append(f"✓ DPI: {dpi} (OK)")

    return issues
```

### 2. Extract Text with OCR

```python
import pytesseract
from PIL import Image

def extract_text_ocr(image_path):
    img = Image.open(image_path)
    # Use eng+jpn for bilingual support
    text = pytesseract.image_to_string(img, lang='eng')
    return text

def extract_numbers(text):
    import re
    pattern = r'\d+\.?\d*'
    numbers = re.findall(pattern, text)
    return [float(n) for n in numbers if '.' in n or int(n) > 0]
```

### 3. Check Consistency

```python
def check_consistency(ocr_numbers, paper_numbers, tolerance=0.01):
    issues = []
    for num in ocr_numbers:
        found = any(abs(num - p) < tolerance for p in paper_numbers)
        if not found and 0 < num < 1000:
            issues.append(f"Number {num} in figure not found in text")
    return issues
```

### 4. Check Table Layout

```python
def check_table_layout(spec):
    issues = []
    for table_id, table in spec.get('tables', {}).items():
        rows = len(table.get('data', []))
        cols = len(table.get('columns', []))

        if rows > 8:
            issues.append(f"⚠ {table_id}: {rows} rows (max recommended: 8)")
        if cols > 6:
            issues.append(f"⚠ {table_id}: {cols} columns (max recommended: 6)")

    return issues
```

## Example Output

```
============================================================
=== Figure QA Report ===
============================================================

[fig_roc]
  ✓ Resolution: 1770x1771 (OK)
  ✓ DPI: 300 (OK)
  OCR detected numbers: [0.872, 0.866, 0.853, 0.857]
  ✓ All key numbers found in text
  ✓ Bilingual captions present

[fig_institution]
  ✓ Resolution: 2371x1471 (OK)
  ✓ DPI: 300 (OK)
  OCR detected numbers: [0.828, 0.830, 0.844, 0.850, 0.876, 0.887]
  ✓ All key numbers found in text
  ✓ Bilingual captions present

[fig_confusion]
  ✓ Resolution: 1802x1216 (OK)
  ✓ DPI: 300 (OK)
  OCR detected numbers: [11404, 56, 780, 144]
  ✓ All key numbers found in text
  ✓ Bilingual captions present

=== Table Layout Check ===
  ✓ tab_demographics: 5 rows, 4 columns (OK)
  ⚠ tab_institution: 6 rows, 4 columns (OK but consider splitting)

=== Consistency Issues ===
  None found

=== Summary ===
  Figures checked: 4
  Errors: 0
  Warnings: 1
  Info items: 0

⚠ Minor issues found. Review warnings above.

=== Recommendations ===
  - Consider splitting tab_institution if layout issues occur
  - Manually verify figure-text consistency
```

## Severity Levels

| Level | Icon | Description | Action |
|-------|------|-------------|--------|
| Error | ✗ | Critical issue | Must fix before build |
| Warning | ⚠ | Potential problem | Review and fix if needed |
| Info | ℹ | Informational | Optional improvement |
| OK | ✓ | Passed check | No action needed |

## Checks Performed

| Check | Severity | Threshold |
|-------|----------|-----------|
| File missing | Error | - |
| Low resolution | Warning | < 600x400 |
| Low DPI | Warning | < 150 |
| Table too long | Warning | > 8 rows |
| Table too wide | Warning | > 6 columns |
| Numbers mismatch | Info | tolerance 0.01 |
| Missing caption | Warning | - |
| Missing bilingual | Warning | - |

## Workflow Integration

Run QA after generating figures, before building PDF:

```
/paper-analyze ./experiment/
/paper-generate ./experiment/ --output ./paper/
/paper-figures ./paper/
/paper-diagrams ./paper/  # If architecture diagram needed
/paper-qa ./paper/        # <-- QA check here
/paper-build ./paper/
```

If issues found:
1. Fix the identified problems
2. Re-run `/paper-qa` to verify
3. Proceed to `/paper-build`

## Tips

- Run QA check every time figures are regenerated
- Pay attention to number consistency warnings
- Keep tables under 8 rows to prevent layout issues
- Use high-contrast figures for better OCR accuracy
- Ensure Japanese language pack is installed for bilingual papers
