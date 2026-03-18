"""
PDF Builder - Converts a paper specification (dict/YAML) into a PDF.

Pipeline: Markdown -> HTML (via Jinja2 templates) -> PDF (via WeasyPrint).
Supports bilingual (EN/JA) output and multiple academic paper templates.
"""

from __future__ import annotations

import os
import html as html_module
from pathlib import Path
from typing import Any

import markdown
from jinja2 import Environment, BaseLoader
from weasyprint import HTML

# ---------------------------------------------------------------------------
# Markdown extensions
# ---------------------------------------------------------------------------
_MD_EXTENSIONS = [
    "tables",
    "footnotes",
    "attr_list",
    "md_in_html",
    "pymdownx.arithmatex",
]

_MD_EXTENSION_CONFIGS = {
    "pymdownx.arithmatex": {
        "generic": True,
    },
}

# ---------------------------------------------------------------------------
# CSS constants
# ---------------------------------------------------------------------------

_CSS_BASE = r"""
/* ===== Reset & Base ===== */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

@page {
    size: A4;
    margin: 25mm 20mm 30mm 20mm;

    @bottom-center {
        content: counter(page);
        font-family: "Times New Roman", "Noto Serif", serif;
        font-size: 9pt;
        color: #444;
    }
}

/* First page: no page number, extra top margin for title block */
@page :first {
    margin-top: 30mm;

    @bottom-center {
        content: none;
    }
}

html {
    font-size: 10pt;
    line-height: 1.5;
    color: #1a1a1a;
    orphans: 3;
    widows: 3;
}

body {
    font-family: "Times New Roman", "Noto Serif", "DejaVu Serif", serif;
    word-wrap: break-word;
    hyphens: auto;
}

/* ===== Title Block ===== */
.paper-title {
    font-size: 17pt;
    font-weight: bold;
    text-align: center;
    line-height: 1.25;
    margin-bottom: 8pt;
    color: #111;
}

.paper-authors {
    text-align: center;
    font-size: 10pt;
    margin-bottom: 4pt;
}

.paper-authors .author-name {
    font-weight: bold;
}

.paper-authors .author-affiliation {
    font-size: 8.5pt;
    color: #555;
}

.paper-date {
    text-align: center;
    font-size: 9pt;
    color: #666;
    margin-bottom: 12pt;
}

.paper-keywords {
    text-align: center;
    font-size: 8.5pt;
    color: #444;
    margin-bottom: 16pt;
    font-style: italic;
}

.paper-keywords strong {
    font-style: normal;
}

/* ===== Horizontal Rule (visual separator) ===== */
hr.title-sep {
    border: none;
    border-top: 0.75pt solid #999;
    margin: 10pt 0 14pt 0;
}

/* ===== Abstract ===== */
.abstract {
    margin: 0 24pt 16pt 24pt;
    page-break-inside: avoid;
}

.abstract h2 {
    font-size: 10pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
    margin-bottom: 4pt;
}

.abstract p {
    font-size: 9.5pt;
    text-align: justify;
    line-height: 1.45;
}

/* ===== Section Headings ===== */
h1, h2, h3, h4, h5, h6 {
    font-family: "Times New Roman", "Noto Serif", "DejaVu Serif", serif;
    color: #111;
    page-break-after: avoid;
}

/* Main section heading: e.g. "1. Introduction" */
.paper-body h2 {
    font-size: 12pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.3pt;
    margin-top: 18pt;
    margin-bottom: 6pt;
    padding-bottom: 2pt;
    border-bottom: 0.5pt solid #ccc;
}

/* Subsection heading */
.paper-body h3 {
    font-size: 11pt;
    font-weight: bold;
    margin-top: 12pt;
    margin-bottom: 4pt;
}

/* Sub-subsection heading */
.paper-body h4 {
    font-size: 10pt;
    font-weight: bold;
    font-style: italic;
    margin-top: 8pt;
    margin-bottom: 3pt;
}

/* ===== Body Content ===== */
.paper-body p {
    text-align: justify;
    text-indent: 1.5em;
    margin-bottom: 4pt;
    line-height: 1.5;
}

/* First paragraph after heading - no indent */
.paper-body h2 + p,
.paper-body h3 + p,
.paper-body h4 + p {
    text-indent: 0;
}

/* ===== Lists ===== */
.paper-body ul, .paper-body ol {
    margin-left: 2em;
    margin-bottom: 6pt;
}

.paper-body li {
    margin-bottom: 2pt;
    text-align: justify;
}

/* ===== Figures ===== */
.figure {
    text-align: center;
    margin: 14pt 0;
    page-break-inside: avoid;
}

.figure img {
    max-width: 100%;
    height: auto;
}

.figure.wide-figure {
    column-span: all;
}

.figure-caption {
    font-size: 9pt;
    text-align: justify;
    margin-top: 6pt;
    line-height: 1.35;
    padding: 0 12pt;
}

.figure-caption .caption-label {
    font-weight: bold;
}

/* ===== Tables ===== */
table {
    border-collapse: collapse;
    width: 100%;
    font-size: 9pt;
    margin: 10pt 0;
    page-break-inside: avoid;
}

table caption {
    font-size: 9pt;
    text-align: justify;
    margin-bottom: 4pt;
    caption-side: top;
}

table caption .caption-label {
    font-weight: bold;
}

/* Booktabs-style rules */
thead {
    border-top: 1.5pt solid #111;
    border-bottom: 0.75pt solid #111;
}

thead th {
    font-weight: bold;
    padding: 4pt 6pt;
    text-align: center;
    vertical-align: bottom;
}

tbody td {
    padding: 3pt 6pt;
    text-align: center;
    vertical-align: top;
}

tbody tr:last-child {
    border-bottom: 1.5pt solid #111;
}

/* Subtle alternating rows */
tbody tr:nth-child(even) {
    background-color: #f8f8f8;
}

/* ===== Acknowledgments ===== */
.acknowledgments {
    margin-top: 18pt;
}

.acknowledgments h2 {
    font-size: 10pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.3pt;
    margin-bottom: 4pt;
}

.acknowledgments p {
    font-size: 9.5pt;
    text-align: justify;
}

/* ===== References ===== */
.references {
    margin-top: 18pt;
}

.references h2 {
    font-size: 10pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.3pt;
    margin-bottom: 6pt;
    border-bottom: 0.5pt solid #ccc;
    padding-bottom: 2pt;
}

.references ol {
    list-style-type: none;
    counter-reset: ref-counter;
    margin-left: 0;
    padding-left: 0;
}

.references ol li {
    counter-increment: ref-counter;
    margin-bottom: 3pt;
    padding-left: 2.2em;
    text-indent: -2.2em;
    font-size: 8.5pt;
    line-height: 1.4;
    text-align: justify;
}

.references ol li::before {
    content: "[" counter(ref-counter) "] ";
    font-weight: bold;
    color: #333;
}

/* ===== Code / Monospace ===== */
code {
    font-family: "Courier New", "DejaVu Sans Mono", monospace;
    font-size: 8.5pt;
    background-color: #f4f4f4;
    padding: 0 2pt;
    border-radius: 2pt;
}

pre {
    background-color: #f4f4f4;
    border: 0.5pt solid #ddd;
    padding: 8pt;
    font-size: 8pt;
    line-height: 1.3;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 8pt 0;
}

pre code {
    background: none;
    padding: 0;
}

/* ===== Math (arithmatex generic output) ===== */
.arithmatex {
    text-align: center;
    margin: 8pt 0;
    font-style: italic;
}

/* ===== Footnotes ===== */
.footnote {
    font-size: 8pt;
    border-top: 0.5pt solid #ccc;
    margin-top: 18pt;
    padding-top: 6pt;
}

.footnote ol {
    margin-left: 1.5em;
}

.footnote li {
    margin-bottom: 2pt;
}

/* ===== Blockquotes ===== */
blockquote {
    border-left: 2pt solid #ccc;
    margin: 8pt 0 8pt 12pt;
    padding-left: 10pt;
    color: #444;
    font-style: italic;
}
"""

_CSS_TWOCOL = """
/* ===== Two-Column Layout ===== */
@page {
    margin: 20mm 15mm 25mm 15mm;
}

.paper-body {
    column-count: 2;
    column-gap: 18pt;
    column-rule: 0.25pt solid #e0e0e0;
}

/* Title block & abstract span full width */
.title-block,
.abstract,
hr.title-sep {
    column-span: all;
}

/* Allow wide figures/tables to span both columns */
.wide-figure,
.wide-table {
    column-span: all;
}

/* References in two-column */
.references {
    column-span: all;
}

/* Acknowledgments span full width */
.acknowledgments {
    column-span: all;
}
"""

_CSS_ONECOL = """
/* ===== One-Column Layout ===== */
.paper-body {
    max-width: 100%;
}
"""

_CSS_NATURE = """
/* ===== Nature-Style Layout ===== */
@page {
    margin: 20mm 18mm 25mm 18mm;
}

.paper-title {
    font-size: 20pt;
    font-family: "Helvetica Neue", "Noto Sans", "Arial", sans-serif;
    font-weight: bold;
    text-align: left;
    color: #000;
    margin-bottom: 10pt;
}

.paper-authors {
    text-align: left;
    font-family: "Helvetica Neue", "Noto Sans", "Arial", sans-serif;
}

.paper-date {
    text-align: left;
}

.paper-keywords {
    text-align: left;
}

.abstract {
    margin: 0 0 16pt 0;
    background-color: #f0f4f8;
    padding: 12pt 14pt;
    border-left: 3pt solid #2563eb;
}

.abstract h2 {
    font-family: "Helvetica Neue", "Noto Sans", "Arial", sans-serif;
    color: #2563eb;
}

.paper-body h2 {
    font-family: "Helvetica Neue", "Noto Sans", "Arial", sans-serif;
    text-transform: none;
    color: #2563eb;
    border-bottom: 1.5pt solid #2563eb;
    font-size: 13pt;
}

.paper-body h3 {
    font-family: "Helvetica Neue", "Noto Sans", "Arial", sans-serif;
    color: #333;
}

.references h2 {
    font-family: "Helvetica Neue", "Noto Sans", "Arial", sans-serif;
    color: #2563eb;
    border-bottom: 1.5pt solid #2563eb;
}
"""

_CSS_IEEE = """
/* ===== IEEE-Style Layout ===== */
@page {
    size: A4;
    margin: 19mm 16mm 25mm 16mm;
}

.paper-title {
    font-size: 22pt;
    font-family: "Times New Roman", "Noto Serif", serif;
    margin-bottom: 12pt;
}

.paper-authors {
    font-size: 10pt;
    margin-bottom: 8pt;
}

.paper-authors .author-name {
    font-size: 11pt;
}

.abstract {
    margin: 0 0 12pt 0;
}

.abstract h2 {
    font-style: italic;
    text-transform: none;
    letter-spacing: 0;
}

.paper-body {
    column-count: 2;
    column-gap: 16pt;
}

.title-block,
.abstract,
hr.title-sep {
    column-span: all;
}

.wide-figure,
.wide-table {
    column-span: all;
}

.references {
    column-span: all;
}

.acknowledgments {
    column-span: all;
}

.paper-body h2 {
    text-align: center;
    font-size: 10pt;
    text-transform: uppercase;
    letter-spacing: 0;
    border-bottom: none;
    font-variant: small-caps;
}

.paper-body h3 {
    font-size: 10pt;
    font-style: italic;
    font-weight: normal;
}

.references ol li {
    font-size: 8pt;
}
"""

_CSS_JA = """
/* ===== Japanese (CJK) Font Support ===== */
body {
    font-family: "Noto Serif CJK JP", "Noto Serif JP", "Yu Mincho",
                 "WenQuanYi Micro Hei", "IPAex Mincho", "MS Mincho",
                 "Times New Roman", "Noto Serif", serif;
    line-height: 1.7;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "Noto Sans CJK JP", "Noto Sans JP", "Yu Gothic",
                 "WenQuanYi Zen Hei", "IPAex Gothic", "MS Gothic",
                 "Helvetica Neue", "Arial", sans-serif;
}

.paper-title {
    font-family: "Noto Sans CJK JP", "Noto Sans JP", "Yu Gothic",
                 "WenQuanYi Zen Hei", "IPAex Gothic", "MS Gothic",
                 "Helvetica Neue", "Arial", sans-serif;
}

/* CJK text does not normally use justification hyphens */
.paper-body p {
    text-indent: 1em;
    hyphens: none;
    text-align: justify;
    text-justify: inter-ideograph;
}

/* Slightly wider line height for Japanese readability */
.paper-body {
    line-height: 1.75;
}

.abstract p {
    line-height: 1.65;
}
"""

# ---------------------------------------------------------------------------
# Map template names to their CSS supplements
# ---------------------------------------------------------------------------
_TEMPLATE_CSS: dict[str, str] = {
    "twocol": _CSS_TWOCOL,
    "onecol": _CSS_ONECOL,
    "nature": _CSS_NATURE,
    "ieee": _CSS_IEEE,
}

# ---------------------------------------------------------------------------
# Main Jinja2 HTML template (embedded)
# ---------------------------------------------------------------------------

_PAPER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="{{ language }}">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
{{ css }}
</style>
</head>
<body>

{# ===== Title Block ===== #}
<div class="title-block">
    <div class="paper-title">{{ title }}</div>

    <div class="paper-authors">
    {% for author in authors %}
        <span class="author-name">{{ author.name }}</span>
        {% if author.affiliation %}
        <br><span class="author-affiliation">{{ author.affiliation }}</span>
        {% endif %}
        {% if not loop.last %}<br>{% endif %}
    {% endfor %}
    </div>

    {% if date %}
    <div class="paper-date">{{ date }}</div>
    {% endif %}

    {% if keywords %}
    <div class="paper-keywords">
        <strong>{% if language == 'ja' %}キーワード{% else %}Keywords{% endif %}:</strong>
        {{ keywords | join(', ') }}
    </div>
    {% endif %}
</div>

<hr class="title-sep">

{# ===== Abstract ===== #}
{% if abstract %}
<div class="abstract">
    <h2>{% if language == 'ja' %}概要{% else %}Abstract{% endif %}</h2>
    {{ abstract }}
</div>
{% endif %}

{# ===== Main Body ===== #}
<div class="paper-body">
{% for section in sections %}
    {{ section.rendered_content }}
{% endfor %}
</div>

{# ===== Acknowledgments ===== #}
{% if acknowledgments %}
<div class="acknowledgments">
    <h2>{% if language == 'ja' %}謝辞{% else %}Acknowledgments{% endif %}</h2>
    {{ acknowledgments }}
</div>
{% endif %}

{# ===== References ===== #}
{% if references %}
<div class="references">
    <h2>{% if language == 'ja' %}参考文献{% else %}References{% endif %}</h2>
    <ol>
    {% for ref in references %}
        <li>{{ ref }}</li>
    {% endfor %}
    </ol>
</div>
{% endif %}

</body>
</html>
"""


# ---------------------------------------------------------------------------
# Helper: localised text extraction
# ---------------------------------------------------------------------------

def _loc(obj: Any, language: str) -> Any:
    """Extract the localised value from a bilingual dict, or return as-is."""
    if isinstance(obj, dict) and (language in obj):
        return obj[language]
    if isinstance(obj, dict) and ("en" in obj):
        # Fallback to English when requested language is missing
        return obj["en"]
    return obj


# ---------------------------------------------------------------------------
# PDFBuilder
# ---------------------------------------------------------------------------

class PDFBuilder:
    """Builds academic-paper PDFs from a structured paper specification dict."""

    def __init__(self) -> None:
        self._md = markdown.Markdown(
            extensions=_MD_EXTENSIONS,
            extension_configs=_MD_EXTENSION_CONFIGS,
        )
        self._jinja_env = Environment(loader=BaseLoader(), autoescape=False)
        self._template = self._jinja_env.from_string(_PAPER_TEMPLATE)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_md(self) -> None:
        """Reset the Markdown converter state between documents."""
        self._md.reset()

    def _md_to_html(self, text: str) -> str:
        """Convert a Markdown string to HTML."""
        self._reset_md()
        return self._md.convert(text)

    def _build_css(self, template_name: str, language: str) -> str:
        """Assemble the full CSS string for the given template and language."""
        css_parts = [_CSS_BASE]
        css_parts.append(_TEMPLATE_CSS.get(template_name, _CSS_ONECOL))
        if language == "ja":
            css_parts.append(_CSS_JA)
        return "\n".join(css_parts)

    def _render_figure(self, fig_id: str, fig_spec: dict, language: str) -> str:
        """Render a single figure block to HTML."""
        caption = _loc(fig_spec.get("caption", ""), language)
        label = fig_spec.get("label", fig_id)
        path = fig_spec.get("path", "")
        wide = fig_spec.get("wide", False)

        css_class = "figure wide-figure" if wide else "figure"
        escaped_path = html_module.escape(str(path))
        escaped_caption = html_module.escape(str(caption))

        return (
            f'<div class="{css_class}" id="{html_module.escape(label)}">'
            f'<img src="{escaped_path}" alt="{escaped_caption}">'
            f'<div class="figure-caption">'
            f'<span class="caption-label">Figure {fig_id}.</span> {escaped_caption}'
            f'</div></div>'
        )

    def _render_table(self, tab_id: str, tab_spec: dict, language: str) -> str:
        """Render a single table block to HTML."""
        caption = _loc(tab_spec.get("caption", ""), language)
        label = tab_spec.get("label", tab_id)
        columns = tab_spec.get("columns", [])
        data = tab_spec.get("data", [])

        escaped_caption = html_module.escape(str(caption))
        wide = tab_spec.get("wide", False)
        css_class = "wide-table" if wide else ""

        parts = [f'<table class="{css_class}" id="{html_module.escape(label)}">']
        parts.append(
            f'<caption><span class="caption-label">Table {tab_id}.</span> '
            f'{escaped_caption}</caption>'
        )

        # Header row
        parts.append("<thead><tr>")
        for col in columns:
            parts.append(f"<th>{html_module.escape(str(col))}</th>")
        parts.append("</tr></thead>")

        # Data rows
        parts.append("<tbody>")
        for row in data:
            parts.append("<tr>")
            for cell in row:
                parts.append(f"<td>{html_module.escape(str(cell))}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

        return "\n".join(parts)

    def _render_section(
        self,
        section: dict,
        figures: dict,
        tables: dict,
        language: str,
    ) -> str:
        """Render one section (with optional subsections) to HTML."""
        heading = _loc(section.get("heading", ""), language)
        content_md = _loc(section.get("content", ""), language)

        # Convert section Markdown to HTML
        body_html = self._md_to_html(content_md) if content_md else ""

        parts: list[str] = []

        # Section heading
        if heading:
            escaped_heading = html_module.escape(str(heading))
            parts.append(f"<h2>{escaped_heading}</h2>")

        parts.append(body_html)

        # Inline figures referenced by this section
        for fig_id in section.get("figures", []):
            if fig_id in figures:
                parts.append(self._render_figure(fig_id, figures[fig_id], language))

        # Inline tables referenced by this section
        for tab_id in section.get("tables", []):
            if tab_id in tables:
                parts.append(self._render_table(tab_id, tables[tab_id], language))

        # Recursively render subsections
        for subsec in section.get("subsections", []):
            sub_heading = _loc(subsec.get("heading", ""), language)
            sub_content = _loc(subsec.get("content", ""), language)
            sub_html = self._md_to_html(sub_content) if sub_content else ""

            if sub_heading:
                escaped_sub = html_module.escape(str(sub_heading))
                parts.append(f"<h3>{escaped_sub}</h3>")
            parts.append(sub_html)

            for fig_id in subsec.get("figures", []):
                if fig_id in figures:
                    parts.append(
                        self._render_figure(fig_id, figures[fig_id], language)
                    )
            for tab_id in subsec.get("tables", []):
                if tab_id in tables:
                    parts.append(
                        self._render_table(tab_id, tables[tab_id], language)
                    )

        return "\n".join(parts)

    def _prepare_context(self, paper_spec: dict, language: str) -> dict:
        """Build the Jinja2 template context from a paper_spec dict."""
        meta = paper_spec.get("meta", {})
        template_name = meta.get("template", "onecol")
        figures = paper_spec.get("figures", {})
        tables = paper_spec.get("tables", {})

        # Render all sections
        rendered_sections = []
        for section in paper_spec.get("sections", []):
            rendered_content = self._render_section(
                section, figures, tables, language
            )
            rendered_sections.append({"rendered_content": rendered_content})

        # Abstract
        abstract_md = _loc(paper_spec.get("abstract", ""), language)
        abstract_html = self._md_to_html(abstract_md) if abstract_md else ""

        # Acknowledgments
        ack_md = _loc(paper_spec.get("acknowledgments", ""), language)
        ack_html = self._md_to_html(ack_md) if ack_md else ""

        # Keywords
        keywords = _loc(meta.get("keywords", []), language)
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]

        # References (normalize dicts to formatted strings)
        raw_refs = paper_spec.get("references", [])
        references = []
        for ref in raw_refs:
            if isinstance(ref, str):
                references.append(ref)
            elif isinstance(ref, dict):
                parts = []
                if ref.get("authors"):
                    parts.append(ref["authors"])
                if ref.get("title"):
                    parts.append(f'"{ref["title"]}"')
                if ref.get("journal"):
                    parts.append(ref["journal"])
                if ref.get("year"):
                    parts.append(str(ref["year"]))
                references.append(", ".join(parts) + ".")
            else:
                references.append(str(ref))

        return {
            "language": language,
            "title": _loc(meta.get("title", "Untitled"), language),
            "authors": paper_spec.get("authors", meta.get("authors", [])),
            "date": meta.get("date", ""),
            "keywords": keywords,
            "abstract": abstract_html,
            "sections": rendered_sections,
            "acknowledgments": ack_html,
            "references": references,
            "css": self._build_css(template_name, language),
        }

    def _render_html(self, paper_spec: dict, language: str) -> str:
        """Render the full HTML document string."""
        context = self._prepare_context(paper_spec, language)
        return self._template.render(**context)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def preview_html(self, paper_spec: dict, language: str = "en") -> str:
        """Return the rendered HTML string for preview (no PDF generation).

        Parameters
        ----------
        paper_spec : dict
            The paper specification dictionary.
        language : str
            Language code, ``"en"`` or ``"ja"``.

        Returns
        -------
        str
            Complete HTML document as a string.
        """
        return self._render_html(paper_spec, language)

    def build(
        self,
        paper_spec: dict,
        output_path: str,
        language: str = "en",
    ) -> str:
        """Build a PDF from the paper specification.

        Parameters
        ----------
        paper_spec : dict
            The paper specification dictionary (see module docstring for schema).
        output_path : str
            File path for the generated PDF.
        language : str
            Language code, ``"en"`` or ``"ja"``.

        Returns
        -------
        str
            The absolute path of the generated PDF file.
        """
        html_string = self._render_html(paper_spec, language)

        # Ensure the output directory exists
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Determine base_url for resolving relative image paths
        base_url = str(out.parent.resolve()) + os.sep

        HTML(string=html_string, base_url=base_url).write_pdf(str(out))

        return str(out.resolve())

    def build_bilingual(
        self,
        paper_spec: dict,
        output_dir: str,
    ) -> tuple[str, str]:
        """Build both English and Japanese PDFs.

        Parameters
        ----------
        paper_spec : dict
            The paper specification dictionary.
        output_dir : str
            Directory where the two PDFs will be saved.

        Returns
        -------
        tuple[str, str]
            ``(en_pdf_path, ja_pdf_path)`` as absolute paths.
        """
        title_slug = (
            _loc(paper_spec.get("meta", {}).get("title", "paper"), "en")
            .lower()
            .replace(" ", "_")[:60]
        )
        # Sanitize the slug to only alphanumerics and underscores
        title_slug = "".join(
            c if c.isalnum() or c == "_" else "_" for c in title_slug
        )

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        en_path = self.build(
            paper_spec,
            str(out_dir / f"{title_slug}_en.pdf"),
            language="en",
        )
        ja_path = self.build(
            paper_spec,
            str(out_dir / f"{title_slug}_ja.pdf"),
            language="ja",
        )

        return (en_path, ja_path)
