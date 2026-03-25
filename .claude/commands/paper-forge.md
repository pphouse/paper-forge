# Paper Forge (Integrated Pipeline)

AI-driven academic paper writing pipeline. Generates publication-ready bilingual (EN/JA) PDFs from experiment data, following EQUATOR Network guidelines (TRIPOD+AI, STARD-AI).

## Usage

```
/paper-forge <experiment_dir> [--journal lancet|nature|jama] [--guideline tripod-ai|stard-ai]
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AI-Driven Paper Writing Pipeline                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │   Agent 1   │    │   Agent 2   │    │   Agent 3   │                  │
│  │   Data      │    │  Literature │    │   Figure    │                  │
│  │  Analysis   │    │   Search    │    │ Generation  │                  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  │
│         │                  │                   │                         │
│         └────────┬─────────┴─────────┬────────┘                         │
│                  ▼                   ▼                                   │
│           ┌─────────────┐     ┌─────────────┐                           │
│           │   Agent 4   │     │   Review    │                           │
│           │   Paper     │────▶│   Quality   │                           │
│           │   Writing   │     │   Check     │                           │
│           └──────┬──────┘     └──────┬──────┘                           │
│                  │                   │                                   │
│                  └─────────┬─────────┘                                   │
│                            ▼                                             │
│                     ┌─────────────┐                                      │
│                     │   LaTeX     │                                      │
│                     │   Build     │                                      │
│                     │  (EN/JA)    │                                      │
│                     └──────┬──────┘                                      │
│                            ▼                                             │
│                     ┌─────────────┐                                      │
│                     │    PDF      │                                      │
│                     │   Output    │                                      │
│                     └─────────────┘                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Full Automated Pipeline

```bash
# Run complete pipeline
/paper-forge ./experiments/model_results/ --journal lancet --guideline tripod-ai

# This executes:
# 1. /paper-analyze   (Agent 1: Data Analysis)
# 2. /paper-literature (Agent 2: Literature Search)
# 3. /paper-figures   (Agent 3: Figure Generation)
# 4. /paper-generate  (Agent 4: Paper Writing + LaTeX)
# 5. /paper-review    (Quality Check)
# 6. /paper-build     (PDF Compilation)
```

### Step-by-Step Execution

```bash
/paper-analyze ./experiments/                    # Agent 1
/paper-literature ./paper_project/               # Agent 2
/paper-figures ./paper_project/                  # Agent 3
/paper-generate ./paper_project/ --journal lancet # Agent 4
/paper-review ./paper_project/                   # Quality Check
/paper-build ./paper_project/ --lang all         # PDF Output
```

## Workflow Phases

### Phase 1: Data Analysis (Agent 1)

```
/paper-analyze <experiment_dir> --domain cardiology
```

**Input:**
- Experiment data (CSV/JSON/images)
- Target journal specification

**Output:**
- `analysis_report.json`: Structured analysis results
- Performance metrics (AUC, sensitivity, specificity, 95% CI)
- Patient demographics
- Keywords for Agent 2

### Phase 2: Literature Search (Agent 2)

```
/paper-literature <project_dir>
```

**Input:**
- Keywords from Agent 1
- Disease/method context

**Output:**
- `literature/search_results.json`: Related papers
- `literature/related_work.md`: Literature review draft
- `literature/references.bib`: BibTeX references
- Novelty assessment vs prior work

### Phase 3: Figure Generation (Agent 3)

```
/paper-figures <project_dir> --journal lancet
```

**Input:**
- Experiment data
- Journal guidelines

**Output:**
- `figures/fig_roc.png`: ROC curve with AUC and 95% CI
- `figures/fig_confusion.png`: Confusion matrix
- `figures/fig_institution.png`: Subgroup analysis
- `tables/table1.csv`: Patient characteristics

### Phase 4: Paper Writing (Agent 4)

```
/paper-generate <project_dir> --journal lancet --guideline tripod-ai
```

**Input:**
- All Agent 1-3 outputs

**Output:**
- `paper_spec.yaml`: Paper specification (bilingual)
- `paper_en.tex`: English LaTeX (TRIPOD+AI compliant)
- `paper_ja.tex`: Japanese LaTeX (XeLaTeX)

### Phase 5: Quality Review

```
/paper-review <project_dir>
```

**Input:**
- paper_spec.yaml
- All figures

**Output:**
- `review_report.md`: Quality assessment
- Improvement suggestions
- Score (target: 80/100+)

### Phase 6: PDF Build

```
/paper-build <project_dir> --lang all
```

**Input:**
- LaTeX source files
- Figures

**Output:**
- `output/paper_en.pdf`: English PDF
- `output/paper_ja.pdf`: Japanese PDF

## EQUATOR Network Compliance

### TRIPOD+AI (27 Items)

For ML prediction model studies:

| Section | Key Requirements |
|---------|------------------|
| Title | Include "development" or "validation" |
| Abstract | Structured: Background, Methods, Findings, Interpretation |
| Methods | Model architecture, hyperparameters, training procedure |
| Results | Performance with 95% CI, subgroup analyses |
| Discussion | Comparison with prior models, limitations |

### Lancet Digital Health Format

1. **Summary Panel** (structured abstract)
2. **Research in Context Panel**
   - Evidence before this study
   - Added value of this study
   - Implications of all available evidence
3. **Introduction** (brief, focused)
4. **Methods** (TRIPOD+AI compliant)
5. **Results** (with inline figures)
6. **Discussion** (Principal findings, Comparison, Implications, Limitations)
7. **Contributors, Data sharing**

### Clinical Utility Metrics

- **Rule-out threshold**: Specificity ≥99% (minimize false positives)
- **Rule-in threshold**: Sensitivity ≥90% (minimize false negatives)

## Output Directory Structure

```
<project_dir>/
├── analysis_report.json      # Agent 1 output
├── literature/               # Agent 2 output
│   ├── search_results.json
│   ├── related_work.md
│   └── references.bib
├── figures/                  # Agent 3 output
│   ├── fig_roc.png
│   ├── fig_confusion.png
│   └── fig_institution.png
├── tables/
│   └── table1.csv
├── paper_spec.yaml           # Agent 4 specification
├── paper_en.tex              # English LaTeX
├── paper_ja.tex              # Japanese LaTeX
├── review_report.md          # Quality review
└── output/                   # Final PDFs
    ├── paper_en.pdf
    └── paper_ja.pdf
```

## Key Features

### Inline Figure Placement

Figures are placed within the Results section, not at the end:

```latex
\section{Results}
\subsection{Model Performance}
The model achieved AUROC 0.857...

\begin{figure}[t]
\centering
\includegraphics[width=\columnwidth]{figures/fig_roc.png}
\caption{\textbf{ROC curve.} AUROC = 0.857 (95\% CI: 0.844-0.869).}
\end{figure}
```

### Bilingual Output

All content generated in both English and Japanese:
- English: pdflatex compilation
- Japanese: XeLaTeX with Hiragino fonts

### Quality Metrics

| Metric | Manual | Automated Target |
|--------|--------|------------------|
| Draft generation time | Weeks-months | <1 day |
| TRIPOD+AI compliance | Variable | 100% |
| Bilingual output | Manual translation | Automatic |
| Figure quality | Variable | 300 DPI |

## Supported Journals

| Journal | Template | Key Requirements |
|---------|----------|------------------|
| Lancet Digital Health | `lancet` | Summary panel, Research in Context |
| Nature Medicine | `nature` | Online Methods, 150-word abstract |
| JAMA | `jama` | Key Points required |
| NEJM | `nejm` | Strict word limits |
| IEEE | `ieee` | Two-column, 8000 words |

## Troubleshooting

### Low Review Score

1. Check `review_report.md` for issues
2. Update `paper_spec.yaml`
3. Re-run `/paper-review`
4. Iterate until score ≥80

### Data Inconsistencies

1. Re-run `/paper-analyze` with latest data
2. Regenerate figures with `/paper-figures`
3. Update LaTeX files

### LaTeX Compilation Errors

```bash
# Check log files
grep -E "^!" paper_en.log
grep "Error" paper_ja.log
```

### Japanese Font Issues

```bash
# macOS - use system fonts
\setCJKmainfont{Hiragino Mincho ProN}
```

## Notes

- **Year**: Always use 2026 for publication dates
- **Guideline**: TRIPOD+AI for ML models, STARD-AI for diagnostic accuracy
- **Quality Target**: Review score ≥80/100
- **Figure Quality**: 300 DPI, journal-compliant
- **Bilingual**: All sections in English and Japanese

## References

- **TRIPOD+AI**: Collins GS, et al. BMJ 2024
- **STARD-AI**: Sounderajah V, et al. Nat Med 2020
- **EQUATOR Network**: https://www.equator-network.org/
