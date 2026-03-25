# Paper Generate (Agent 4: EQUATOR-Compliant Paper Writing)

AI-driven paper writing agent that generates EQUATOR Network-compliant manuscripts following TRIPOD+AI (for ML prediction models) or STARD-AI (for diagnostic accuracy studies) guidelines.

## Usage

```
/paper-generate <project_dir> [--journal lancet|nature|jama|nejm|ieee] [--guideline tripod-ai|stard-ai]
```

## What This Does

Integrates outputs from Agent 1 (data analysis), Agent 2 (literature search), and Agent 3 (figures) to generate:

1. **paper_spec.yaml** - Structured paper specification (bilingual)
2. **paper_en.tex** - LaTeX source (English, TRIPOD+AI compliant)
3. **paper_ja.tex** - LaTeX source (Japanese, XeLaTeX)

## EQUATOR Network Guidelines

### TRIPOD+AI (27 Items) - For ML Prediction Models

Key checklist items to address:

| # | Section | Item |
|---|---------|------|
| 1 | Title | Study type (development, validation, both) |
| 2 | Abstract | Structured: Background, Methods, Findings, Interpretation |
| 3 | Introduction | Intended use, clinical context |
| 4 | Methods | Data sources with dates, inclusion/exclusion |
| 5 | Methods | Model architecture, hyperparameters |
| 6 | Methods | Training procedure, validation strategy |
| 7 | Results | Sample size, demographics, outcome prevalence |
| 8 | Results | Performance metrics with 95% CI |
| 9 | Results | Subgroup analyses |
| 10 | Discussion | Comparison with existing models |
| 11 | Discussion | Limitations (data, model, generalizability) |

### STARD-AI (40 Items) - For Diagnostic Accuracy

Additional requirements:
- Clear reference standard definition
- Multiple threshold reporting
- Clinical utility metrics (rule-out, rule-in)

## Journal Templates

### Lancet Digital Health (Recommended for AI/ML)

Structure:
1. **Summary Panel** (structured abstract)
2. **Research in Context Panel**
   - Evidence before this study
   - Added value of this study
   - Implications of all available evidence
3. **Introduction** (brief, focused)
4. **Methods** (detailed, TRIPOD+AI compliant)
5. **Results** (with inline figures)
6. **Discussion** (Principal findings, Comparison, Implications, Limitations)
7. **Contributors, Data sharing, Declaration of interests**

### Word Limits

| Journal | Abstract | Main Text | References |
|---------|----------|-----------|------------|
| Lancet Digital Health | 300 (structured) | 3500 | 30 |
| Nature Medicine | 150 (unstructured) | 3000 | 50 |
| JAMA | 350 (structured) | 3000 | 40 |

## Implementation

### Step 1: Load Agent Outputs

```python
import json
import yaml
from pathlib import Path

# Agent 1: Analysis results
with open(f'{project_dir}/analysis_report.json') as f:
    analysis = json.load(f)

# Agent 2: Literature
with open(f'{project_dir}/literature/search_results.json') as f:
    literature = json.load(f)

# Agent 3: Figures
figures = list(Path(f'{project_dir}/figures').glob('fig_*.png'))
```

### Step 2: Generate Structured Content

#### Summary Panel (Abstract)

```markdown
**Background:** [Disease] is a [prevalence] condition affecting [population].
Early detection is challenging due to [barrier]. We developed a multimodal
deep learning model combining [modalities] for [disease] detection.

**Methods:** This retrospective, multicenter study included [N] patients from
[N_institutions] institutions in Japan ([date range]). We trained a [model type]
using 3-fold cross-validation. Performance was evaluated using AUROC with
bootstrap 95% CI.

**Findings:** The model achieved AUROC [AUC] (95% CI: [lower]-[upper]).
At specificity ≥99% (rule-out threshold), sensitivity was [sens]%.
At sensitivity ≥90% (rule-in threshold), specificity was [spec]%.
Performance was consistent across institutions (AUROC range: [min]-[max]).

**Interpretation:** [Modality] deep learning shows high accuracy for [disease]
detection. This approach may enable population-level screening in primary care.

**Funding:** [Funding sources]
```

#### Research in Context Panel

```markdown
**Evidence before this study:**
We searched PubMed and Google Scholar for studies on AI-based [disease]
detection using [modalities], published before [date]. Previous single-center
studies reported AUC of [range]. However, multicenter validation was lacking.

**Added value of this study:**
This is the first large-scale multicenter validation of [modality]-based
[disease] detection, demonstrating consistent performance across [N]
institutions with [N] patients. We established clinical utility thresholds.

**Implications of all available evidence:**
[Modality] deep learning could enable accessible [disease] screening in
resource-limited settings. Prospective validation studies are warranted.
```

#### Methods - TRIPOD+AI Compliant

```markdown
## Methods

### Study design and participants
This retrospective diagnostic accuracy study included consecutive adult
patients (≥18 years) from [N] academic medical centers in Japan ([names]).
Inclusion: [modality] within 30 days of echocardiography ([date range]).
Exclusion: prior [intervention], poor quality data, missing reference standard.

[Disease] was defined as [criteria] according to current guidelines.
The study was approved by institutional review boards (approval numbers: [...]).

### Model development
We developed a multimodal deep learning model with:
- **ECG encoder:** 1D-CNN processing raw waveform (500 Hz, 10 seconds)
- **Chest X-ray encoder:** ResNet-50 pretrained on ImageNet
- **Fusion:** Feature concatenation followed by fully connected layers

Training: 3-fold cross-validation, Adam optimizer (learning rate = 3×10⁻⁵),
batch size = 32, 100 epochs with early stopping.

### Statistical analysis
Primary outcome: AUROC with 95% CI (bootstrap, n=1000).
Secondary: sensitivity, specificity, PPV, NPV at predefined thresholds.
Clinical utility: rule-out threshold (specificity ≥99%), rule-in threshold
(sensitivity ≥90%).
Subgroup: institution-level AUROCs with I² heterogeneity statistic.
Software: Python 3.10, scikit-learn 1.2, PyTorch 2.0.
```

#### Results - With Inline Figures

```markdown
## Results

### Patient characteristics
[N_total] patients were included (mean age [age] ± [sd] years, [male%] male).
[N_positive] ([prevalence]%) had [disease] (Table 1).

### Model performance
The model achieved AUROC [AUC] (95% CI: [lower]-[upper]) (Figure 1).

[INLINE FIGURE 1: ROC curve]

At the optimal threshold ([threshold]), sensitivity was [sens]% and
specificity was [spec]%. The confusion matrix showed [TP] true positives,
[TN] true negatives, [FP] false positives, [FN] false negatives (Figure 2).

[INLINE FIGURE 2: Confusion matrix]

### Clinical utility
At specificity ≥99% (rule-out threshold = [value]), sensitivity was [sens]%.
At sensitivity ≥90% (rule-in threshold = [value]), specificity was [spec]%.

### Subgroup analyses
Performance was consistent across institutions (Figure 3):
- [Institution 1]: AUROC [AUC] (n=[N])
- [Institution 2]: AUROC [AUC] (n=[N])
...

I² = [value]% indicating [low/moderate/high] heterogeneity.

[INLINE FIGURE 3: Institution performance]
```

### Step 3: Generate LaTeX Files

Generate both English and Japanese versions with:
- Summary panel at top (onecolumn)
- Research in context panel
- Main text (twocolumn)
- Inline figures in Results section
- Tables at end

See `/paper-build` for LaTeX templates.

## paper_spec.yaml Format

```yaml
meta:
  title:
    en: "Multimodal Deep Learning for Detection of Aortic Stenosis..."
    ja: "心電図と胸部X線を用いたマルチモーダル深層学習..."
  template: lancet
  guideline: tripod-ai
  date: "2026"

panels:
  summary:
    background:
      en: "Aortic stenosis (AS) is a progressive..."
      ja: "大動脈弁狭窄症（AS）は進行性の..."
    methods:
      en: "This retrospective, multicenter..."
      ja: "本後ろ向き多施設研究は..."
    findings:
      en: "The model achieved AUROC 0.857..."
      ja: "モデルはAUROC 0.857を達成..."
    interpretation:
      en: "Multimodal deep learning shows..."
      ja: "マルチモーダル深層学習は..."
    funding:
      en: "[Funding sources]"
      ja: "[研究資金]"

  research_in_context:
    evidence_before:
      en: "We searched PubMed..."
      ja: "PubMedを検索し..."
    added_value:
      en: "This is the first..."
      ja: "本研究は初めて..."
    implications:
      en: "ECG and chest X-ray..."
      ja: "心電図と胸部X線..."

sections:
  - heading:
      en: "Introduction"
      ja: "はじめに"
    content:
      en: "[Introduction text]"
      ja: "[はじめに本文]"

  - heading:
      en: "Methods"
      ja: "方法"
    subsections:
      - heading: {en: "Study design and participants", ja: "研究デザインと対象"}
        content: {...}
      - heading: {en: "Model development", ja: "モデル開発"}
        content: {...}
      - heading: {en: "Statistical analysis", ja: "統計解析"}
        content: {...}

  - heading:
      en: "Results"
      ja: "結果"
    content: {...}
    figures: [fig_roc, fig_confusion, fig_institution]  # Inline placement
    tables: [tab_characteristics]

  - heading:
      en: "Discussion"
      ja: "考察"
    subsections:
      - heading: {en: "Principal findings", ja: "主要な知見"}
      - heading: {en: "Comparison with previous studies", ja: "先行研究との比較"}
      - heading: {en: "Clinical implications", ja: "臨床的意義"}
      - heading: {en: "Limitations", ja: "限界"}
      - heading: {en: "Conclusions", ja: "結論"}

figures:
  fig_roc:
    path: "figures/fig_roc.png"
    caption:
      en: "**ROC curve for AS detection.** AUROC = 0.857 (95% CI: 0.844-0.869)..."
      ja: "**AS検出のROC曲線。** AUROC = 0.857（95%信頼区間：0.844-0.869）..."
    placement: inline  # Place in Results section
    wide: false

  fig_confusion:
    path: "figures/fig_confusion.png"
    caption:
      en: "**Confusion matrix at optimal threshold (0.033).**..."
      ja: "**最適閾値（0.033）での混同行列。**..."
    placement: inline
    wide: false

  fig_institution:
    path: "figures/fig_institution.png"
    caption:
      en: "**Institution-wise model performance.**..."
      ja: "**施設別モデル性能。**..."
    placement: inline
    wide: true  # Spans both columns

tables:
  tab_characteristics:
    caption:
      en: "Patient characteristics"
      ja: "患者特性"
    placement: end  # Tables at end of paper
```

## Writing Guidelines

### TRIPOD+AI Compliance
- Include all 27 checklist items
- Report performance metrics with 95% CI
- Describe model architecture in detail
- Document preprocessing and feature engineering
- Report training/validation/test split strategy

### Clinical Utility
- Define rule-out threshold (high specificity, minimize false positives)
- Define rule-in threshold (high sensitivity, minimize false negatives)
- Calculate PPV/NPV at each threshold

### Figure Placement
- Place figures **inline** within relevant section
- Use `placement: inline` in paper_spec.yaml
- Wide figures use `figure*` environment in LaTeX

### Bilingual Content
- Generate BOTH English and Japanese
- Japanese: Natural academic style (学術的な日本語)
- Consistent terminology between languages

## Next Steps

After `/paper-generate`:
1. `/paper-review` - Automated quality review
2. `/paper-build` - Compile to PDF

## Notes

- **Year**: Always use 2026 for dates
- **Guideline**: TRIPOD+AI for ML models, STARD-AI for diagnostic studies
- **Template**: `lancet` recommended for AI/ML papers
