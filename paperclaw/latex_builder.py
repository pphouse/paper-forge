"""
LaTeX-based PDF Builder for PaperClaw.

Pipeline: paper_spec dict -> LaTeX (via Jinja2) -> PDF (via XeLaTeX).
Uses XeLaTeX for proper Unicode / CJK font handling.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jinja2 import Environment, BaseLoader


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _loc(obj: Any, language: str) -> Any:
    """Extract localised value from a bilingual dict."""
    if isinstance(obj, dict) and language in obj:
        return obj[language]
    if isinstance(obj, dict) and "en" in obj:
        return obj["en"]
    return obj if obj else ""


def _escape_latex(text: str) -> str:
    """Escape LaTeX special characters, preserving Markdown-converted LaTeX commands."""
    if not text:
        return ""
    # Characters that need escaping in LaTeX
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _md_to_latex(text: str) -> str:
    """Convert simple Markdown to LaTeX.

    Handles: bold, italic, code, tables, lists, headings.
    Does NOT escape LaTeX specials inside the conversion -
    the raw text should already be safe or intentionally contain LaTeX.
    """
    if not text:
        return ""

    lines = text.strip().split('\n')
    result = []
    in_table = False
    table_rows = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # --- Tables ---
        if '|' in stripped and not stripped.startswith('```'):
            cols = [c.strip() for c in stripped.split('|')]
            cols = [c for c in cols if c != '']  # remove empties from leading/trailing |

            # Separator row (|---|---|)
            if all(re.match(r'^[-:]+$', c) for c in cols):
                continue

            if not in_table:
                in_table = True
                table_rows = []

            table_rows.append(cols)
            continue
        else:
            if in_table:
                result.append(_build_latex_table(table_rows))
                in_table = False
                table_rows = []

        # --- Lists ---
        list_match = re.match(r'^[-*]\s+(.+)$', stripped)
        num_match = re.match(r'^\d+\.\s+(.+)$', stripped)
        if list_match:
            if not in_list:
                result.append(r'\begin{itemize}')
                in_list = True
            result.append(r'  \item ' + _inline_md(list_match.group(1)))
            continue
        elif num_match:
            if not in_list:
                result.append(r'\begin{enumerate}')
                in_list = True
            result.append(r'  \item ' + _inline_md(num_match.group(1)))
            continue
        else:
            if in_list:
                # detect which list type
                if result and r'\begin{enumerate}' in '\n'.join(result[-10:]):
                    result.append(r'\end{enumerate}')
                else:
                    result.append(r'\end{itemize}')
                in_list = False

        # --- Headings (## -> subsection, ### -> subsubsection) ---
        h_match = re.match(r'^(#{2,4})\s+(.+)$', stripped)
        if h_match:
            level = len(h_match.group(1))
            title = _inline_md(h_match.group(2))
            if level == 2:
                result.append(f'\\subsection{{{title}}}')
            elif level == 3:
                result.append(f'\\subsubsection{{{title}}}')
            else:
                result.append(f'\\paragraph{{{title}}}')
            continue

        # --- Blank line -> paragraph break ---
        if not stripped:
            result.append('')
            continue

        # --- Regular paragraph ---
        result.append(_inline_md(stripped))

    # Close open environments
    if in_table:
        result.append(_build_latex_table(table_rows))
    if in_list:
        result.append(r'\end{itemize}')

    return '\n'.join(result)


def _inline_md(text: str) -> str:
    """Convert inline Markdown (bold, italic, code) to LaTeX."""
    # Bold: **text** -> \textbf{text}
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    # Italic: *text* -> \textit{text}
    text = re.sub(r'\*(.+?)\*', r'\\textit{\1}', text)
    # Inline code: `text` -> \texttt{text}
    text = re.sub(r'`(.+?)`', r'\\texttt{\1}', text)
    # Escape LaTeX special characters that appear in natural text
    # (after Markdown conversion so we don't break * syntax)
    text = text.replace('%', r'\%')
    text = text.replace('&', r'\&')
    text = text.replace('_', r'\_')
    text = text.replace('#', r'\#')
    return text


def _build_latex_table(rows: list[list[str]]) -> str:
    """Build a LaTeX booktabs table from parsed rows."""
    if not rows:
        return ""
    ncols = max(len(r) for r in rows)
    col_spec = 'l' + 'c' * (ncols - 1)

    lines = [
        r'\begin{table}[htbp]',
        r'\centering',
        f'\\begin{{tabular}}{{{col_spec}}}',
        r'\toprule',
    ]

    for i, row in enumerate(rows):
        # Pad row
        while len(row) < ncols:
            row.append('')
        cells = [_inline_md(c) for c in row]
        lines.append(' & '.join(cells) + r' \\')
        if i == 0:
            lines.append(r'\midrule')

    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# LaTeX Templates
# ---------------------------------------------------------------------------

_LATEX_PREAMBLE_EN = r"""
\documentclass[10pt,a4paper%(twocol)s]{article}

\usepackage{fontspec}
\setmainfont{Times New Roman}[
  BoldFont = {Times New Roman Bold},
  ItalicFont = {Times New Roman Italic},
  BoldItalicFont = {Times New Roman Bold Italic},
]
\setsansfont{Helvetica}
\setmonofont{Courier New}

\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath,amssymb}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}
\usepackage{caption}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[margin=%(margin)s]{geometry}
\usepackage{xcolor}
\usepackage{authblk}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{microtype}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

\titleformat{\section}{\large\bfseries\uppercase}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\normalsize\itshape}{\thesubsubsection}{0.5em}{}
"""

_LATEX_PREAMBLE_JA = r"""
\documentclass[10pt,a4paper%(twocol)s]{article}

\usepackage{fontspec}
\usepackage{xeCJK}
\setCJKmainfont{Hiragino Mincho ProN}
\setCJKsansfont{Hiragino Sans}
\setCJKmonofont{Osaka-Mono}
\setmainfont{Times New Roman}[
  BoldFont = {Times New Roman Bold},
  ItalicFont = {Times New Roman Italic},
  BoldItalicFont = {Times New Roman Bold Italic},
]
\setsansfont{Helvetica}
\setmonofont{Courier New}

\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{amsmath,amssymb}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}
\usepackage{caption}
\usepackage{float}
\usepackage{fancyhdr}
\usepackage[margin=%(margin)s]{geometry}
\usepackage{xcolor}
\usepackage{authblk}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{microtype}

\XeTeXlinebreaklocale "ja"
\XeTeXlinebreakskip=0pt plus 1pt minus 0.1pt

\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

\titleformat{\section}{\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection}{0.5em}{}
\titleformat{\subsubsection}{\normalsize\itshape}{\thesubsubsection}{0.5em}{}
"""

_LATEX_BODY = r"""
\title{ %(title)s }
%(author_block)s
\date{ %(date)s }

\begin{document}
\maketitle

%(keywords_block)s

\begin{abstract}
%(abstract)s
\end{abstract}

%(body)s

%(acknowledgments_block)s

%(references_block)s

\end{document}
"""

# Template-specific settings
_TEMPLATE_SETTINGS = {
    "twocol": {"twocol": ",twocolumn", "margin": "20mm"},
    "onecol": {"twocol": "", "margin": "25mm"},
    "nature": {"twocol": "", "margin": "22mm"},
    "ieee":   {"twocol": ",twocolumn", "margin": "18mm"},
}


# ---------------------------------------------------------------------------
# LaTeXBuilder
# ---------------------------------------------------------------------------

class LaTeXBuilder:
    """Builds academic-paper PDFs from a structured paper specification using XeLaTeX."""

    def _render_section(self, section: dict, figures: dict, tables: dict,
                        language: str) -> str:
        """Render one section to LaTeX."""
        heading = _loc(section.get("heading", ""), language)
        content_md = _loc(section.get("content", ""), language)
        content_latex = _md_to_latex(content_md) if content_md else ""

        parts = []
        if heading:
            parts.append(f'\\section{{{_inline_md(heading)}}}')
        if content_latex:
            parts.append(content_latex)

        # Figures
        for fig_id in section.get("figures", []):
            if fig_id in figures:
                fig = figures[fig_id]
                path = fig.get("path", "")
                caption = _loc(fig.get("caption", ""), language)
                label = fig.get("label", f"fig:{fig_id}")
                wide = fig.get("wide", False)
                env = "figure*" if wide else "figure"
                # Use [H] for strict placement to avoid overlap issues
                parts.append(f'\\begin{{{env}}}[H]')
                parts.append(r'\centering')
                # Use columnwidth for single column, textwidth for wide figures
                width = r'0.95\textwidth' if wide else r'0.95\columnwidth'
                parts.append(f'\\includegraphics[width={width},keepaspectratio]{{{path}}}')
                parts.append(f'\\caption{{{_inline_md(caption)}}}')
                parts.append(f'\\label{{{label}}}')
                parts.append(f'\\end{{{env}}}')

        # Tables
        for tab_id in section.get("tables", []):
            if tab_id in tables:
                tab = tables[tab_id]
                caption = _loc(tab.get("caption", ""), language)
                label = tab.get("label", f"tab:{tab_id}")
                columns = tab.get("columns", [])
                data = tab.get("data", [])
                if columns and data:
                    ncols = len(columns)
                    col_spec = 'l' + 'c' * (ncols - 1)
                    parts.append(r'\begin{table}[htbp]')
                    parts.append(r'\centering')
                    parts.append(f'\\caption{{{_inline_md(caption)}}}')
                    parts.append(f'\\label{{{label}}}')
                    parts.append(f'\\begin{{tabular}}{{{col_spec}}}')
                    parts.append(r'\toprule')
                    parts.append(' & '.join(_inline_md(c) for c in columns) + r' \\')
                    parts.append(r'\midrule')
                    for row in data:
                        parts.append(' & '.join(_inline_md(str(c)) for c in row) + r' \\')
                    parts.append(r'\bottomrule')
                    parts.append(r'\end{tabular}')
                    parts.append(r'\end{table}')

        # Subsections
        for subsec in section.get("subsections", []):
            sub_heading = _loc(subsec.get("heading", ""), language)
            sub_content = _loc(subsec.get("content", ""), language)
            sub_latex = _md_to_latex(sub_content) if sub_content else ""
            if sub_heading:
                parts.append(f'\\subsection{{{_inline_md(sub_heading)}}}')
            if sub_latex:
                parts.append(sub_latex)

            for fig_id in subsec.get("figures", []):
                if fig_id in figures:
                    fig = figures[fig_id]
                    path = fig.get("path", "")
                    caption = _loc(fig.get("caption", ""), language)
                    label = fig.get("label", f"fig:{fig_id}")
                    parts.append(r'\begin{figure}[H]')
                    parts.append(r'\centering')
                    parts.append(f'\\includegraphics[width=0.95\\columnwidth,keepaspectratio]{{{path}}}')
                    parts.append(f'\\caption{{{_inline_md(caption)}}}')
                    parts.append(f'\\label{{{label}}}')
                    parts.append(r'\end{figure}')

        return '\n\n'.join(parts)

    def _build_latex(self, paper_spec: dict, language: str) -> str:
        """Build complete LaTeX source."""
        meta = paper_spec.get("meta", {})
        template_name = meta.get("template", "onecol")
        settings = _TEMPLATE_SETTINGS.get(template_name, _TEMPLATE_SETTINGS["onecol"])
        figures = paper_spec.get("figures", {})
        tables = paper_spec.get("tables", {})

        # Preamble
        preamble_tpl = _LATEX_PREAMBLE_JA if language == "ja" else _LATEX_PREAMBLE_EN
        preamble = preamble_tpl % settings

        # Title
        title = _loc(meta.get("title", "Untitled"), language)

        # Authors
        authors = paper_spec.get("authors", meta.get("authors", []))
        author_lines = []
        for a in authors:
            if isinstance(a, str):
                author_lines.append(f'\\author{{{a}}}')
            elif isinstance(a, dict):
                name = a.get("name", "")
                aff = a.get("affiliation", "")
                if aff:
                    author_lines.append(f'\\author{{{name}}}')
                    author_lines.append(f'\\affil{{{aff}}}')
                else:
                    author_lines.append(f'\\author{{{name}}}')
        author_block = '\n'.join(author_lines) if author_lines else ''

        # Keywords
        keywords = _loc(paper_spec.get("keywords", meta.get("keywords", "")), language)
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
        if isinstance(keywords, str) and keywords.strip():
            kw_label = "キーワード" if language == "ja" else "Keywords"
            keywords_block = f'\\noindent\\textbf{{{kw_label}:}} {keywords}\n\\vspace{{8pt}}'
        else:
            keywords_block = ""

        # Abstract
        abstract_md = _loc(paper_spec.get("abstract", ""), language)
        abstract = _md_to_latex(abstract_md) if abstract_md else ""

        # Body sections
        body_parts = []
        for section in paper_spec.get("sections", []):
            body_parts.append(self._render_section(section, figures, tables, language))
        body = '\n\n'.join(body_parts)

        # Acknowledgments
        ack_md = _loc(paper_spec.get("acknowledgments", ""), language)
        if ack_md and ack_md.strip():
            ack_label = "謝辞" if language == "ja" else "Acknowledgments"
            ack_latex = _md_to_latex(ack_md)
            acknowledgments_block = f'\\section*{{{ack_label}}}\n{ack_latex}'
        else:
            acknowledgments_block = ""

        # References
        raw_refs = paper_spec.get("references", [])
        if raw_refs:
            ref_label = "参考文献" if language == "ja" else "References"
            ref_items = []
            for ref in raw_refs:
                if isinstance(ref, str):
                    ref_items.append(f'\\bibitem{{}} {ref}')
                elif isinstance(ref, dict):
                    key = ref.get("key", "")
                    parts = []
                    if ref.get("authors"):
                        parts.append(ref["authors"])
                    if ref.get("title"):
                        parts.append(f'\\textit{{{ref["title"]}}}')
                    if ref.get("journal"):
                        parts.append(ref["journal"])
                    if ref.get("year"):
                        parts.append(str(ref["year"]))
                    text = ". ".join(parts) + "."
                    ref_items.append(f'\\bibitem{{{key}}} {text}')

            references_block = (
                f'\\renewcommand{{\\refname}}{{{ref_label}}}\n'
                f'\\begin{{thebibliography}}{{99}}\n' +
                '\n'.join(ref_items) +
                f'\n\\end{{thebibliography}}'
            )
        else:
            references_block = ""

        date = meta.get("date", "")

        # Assemble
        latex = preamble + _LATEX_BODY % {
            "title": _inline_md(title),
            "author_block": author_block,
            "date": date,
            "keywords_block": keywords_block,
            "abstract": abstract,
            "body": body,
            "acknowledgments_block": acknowledgments_block,
            "references_block": references_block,
        }

        return latex

    def build(self, paper_spec: dict, output_path: str, language: str = "en") -> str:
        """Build PDF via XeLaTeX.

        Returns absolute path to generated PDF.
        """
        latex_source = self._build_latex(paper_spec, language)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            tex_file = tmpdir / "paper.tex"
            tex_file.write_text(latex_source, encoding="utf-8")

            # Copy figures into tmpdir if they exist
            project_dir = out.parent.parent  # output_path is in output/
            for fig_id, fig_data in paper_spec.get("figures", {}).items():
                fig_path = Path(fig_data.get("path", ""))
                src = project_dir / fig_path
                if src.exists():
                    dest = tmpdir / fig_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)

            # Run XeLaTeX twice (for cross-references)
            for i in range(2):
                result = subprocess.run(
                    ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode != 0 and i == 1:
                    # Extract error from log
                    log_text = result.stdout or ""
                    errors = [l for l in log_text.split('\n') if l.startswith('!')]
                    error_msg = '\n'.join(errors[:5]) if errors else "XeLaTeX compilation failed"
                    raise RuntimeError(f"XeLaTeX error:\n{error_msg}")

            pdf_file = tmpdir / "paper.pdf"
            if not pdf_file.exists():
                raise RuntimeError("PDF was not generated by XeLaTeX")

            shutil.copy2(pdf_file, out)

        return str(out.resolve())

    def build_bilingual(self, paper_spec: dict, output_dir: str) -> tuple[str, str]:
        """Build both EN and JA PDFs."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        en_path = self.build(paper_spec, str(out_dir / "paper_en.pdf"), language="en")
        ja_path = self.build(paper_spec, str(out_dir / "paper_ja.pdf"), language="ja")
        return (en_path, ja_path)

    def get_latex_source(self, paper_spec: dict, language: str = "en") -> str:
        """Return the generated LaTeX source for inspection/editing."""
        return self._build_latex(paper_spec, language)
