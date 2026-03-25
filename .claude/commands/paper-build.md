# Paper Build

Build publication-quality PDF from LaTeX source files (EN + JA simultaneously).

## Usage

```
/paper-build <project_dir> [--lang en|ja|all]
```

## Output Format (CLIDAS Style)

Papers are generated in clean academic format:
- Clean title (no panels/boxes)
- "CLIDAS Research Group" as author
- Keywords section
- **Plain text abstract** (no Background/Methods labels)
- Numbered sections: 1. INTRODUCTION, 2. METHODS, 3. RESULTS, etc.
- **In-text citations** using `\cite{key}` (e.g., [1], [2,3])
- Inline figures (no grid, clean spines)
- Tables with booktabs formatting
- References at end with `\bibitem{key}`

## Citation Style

Use in-text citations with `\cite{}`:

```latex
% In text
Aortic stenosis affects 2--7\% of adults \cite{otto2021}.
Several studies have shown... \cite{cohen2021,kwon2020}.

% References section
\begin{thebibliography}{9}
\bibitem{otto2021}
Otto CM, et al. 2020 ACC/AHA Guideline... \textit{Circulation}. 2021.
\bibitem{attia2019}
Attia ZI, et al. AI-enabled ECG... \textit{The Lancet}. 2019.
\end{thebibliography}
```

## Figure Style Requirements

**IMPORTANT:** All figures must be generated with:
- No grid lines (`axes.grid = False`)
- No top/right spines
- White background
- Clean legend (no frame)

```python
plt.rcParams['axes.grid'] = False
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False
plt.rcParams['legend.frameon'] = False
plt.rcParams['figure.facecolor'] = 'white'
```

## LaTeX Template (English)

```latex
\documentclass[10pt,twocolumn]{article}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage[margin=2.5cm]{geometry}
\usepackage{hyperref}
\usepackage{caption}
\usepackage{float}
\usepackage{times}

\title{\Large\bfseries [Paper Title]}

\author{CLIDAS Research Group\\[0.3em]
\normalsize Clinical Data Science Consortium, Japan\\[0.5em]
\normalsize 2026}

\date{}

\begin{document}

\maketitle

\noindent\textbf{Keywords:} keyword1, keyword2, ...

\begin{abstract}
% Plain text - NO labels like "Background:" or "Methods:"
Aortic stenosis (AS) is an increasingly prevalent valvular heart disease...
We developed and validated a multimodal deep learning model...
The model achieved AUC of 0.857 (95\% CI: 0.844--0.869)...
Our multimodal approach demonstrates consistent performance...
\end{abstract}

\section{Introduction}
...

\section{Methods}
\subsection{Study Design and Population}
...

\section{Results}
...

\section{Discussion}
...

\section{Conclusion}
...

\end{document}
```

## LaTeX Template (Japanese - XeLaTeX)

```latex
\documentclass[10pt,twocolumn]{article}
\usepackage{xeCJK}
\setCJKmainfont{Hiragino Mincho ProN}
\setCJKsansfont{Hiragino Kaku Gothic ProN}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath}
\usepackage[margin=2.5cm]{geometry}
\usepackage{hyperref}
\usepackage{caption}
\usepackage{float}

\title{\Large\bfseries [日本語タイトル]}

\author{CLIDAS Research Group\\[0.3em]
\normalsize Clinical Data Science Consortium, Japan\\[0.5em]
\normalsize 2026}

\date{}

\begin{document}

\maketitle

\noindent\textbf{Keywords:} aortic stenosis, deep learning, ...

\begin{abstract}
% 日本語要旨（ラベルなし）
大動脈弁狭窄症（AS）は...
\end{abstract}

\section{はじめに}
...

\section{方法}
\subsection{研究デザインと対象}
...

\section{結果}
...

\section{考察}
...

\section{結論}
...

\end{document}
```

## Compilation (Both Languages)

```bash
cd <project_dir>

# English (pdflatex - run twice for references)
pdflatex -interaction=nonstopmode paper_en.tex
pdflatex -interaction=nonstopmode paper_en.tex

# Japanese (xelatex - run twice for references)
xelatex -interaction=nonstopmode paper_ja.tex
xelatex -interaction=nonstopmode paper_ja.tex

# Move to output
mkdir -p output
mv paper_en.pdf paper_ja.pdf output/
```

## Output

```
project_dir/
  paper_en.tex          # English source
  paper_ja.tex          # Japanese source
  figures/
    fig_roc.png         # Clean style (no grid)
    fig_confusion.png
    fig_institution.png
  output/
    paper_en.pdf        # English PDF
    paper_ja.pdf        # Japanese PDF
```

## Troubleshooting

### Grid lines appearing in figures
Regenerate figures with:
```python
plt.style.use('default')
plt.rcParams['axes.grid'] = False
```

### Japanese font issues
```latex
\setCJKmainfont{Hiragino Mincho ProN}
```

### Abstract has labels
Remove "Background:", "Methods:", etc. Use plain text only.
