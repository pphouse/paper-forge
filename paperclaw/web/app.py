"""PaperClaw web application -- interactive editor for research papers."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import markdown
import yaml
from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)

# ---------------------------------------------------------------------------
# Default project directory
# ---------------------------------------------------------------------------
DEFAULT_PROJECTS_DIR = os.path.expanduser("~/paperclaw-projects")

# ---------------------------------------------------------------------------
# Default paper spec template
# ---------------------------------------------------------------------------
DEFAULT_SPEC: dict = {
    "title": {"en": "Untitled Paper", "ja": "無題の論文"},
    "authors": [],
    "abstract": {"en": "", "ja": ""},
    "sections": [
        {"heading": {"en": "Introduction", "ja": "はじめに"}, "body": {"en": "", "ja": ""}},
        {"heading": {"en": "Methods", "ja": "手法"}, "body": {"en": "", "ja": ""}},
        {"heading": {"en": "Results", "ja": "結果"}, "body": {"en": "", "ja": ""}},
        {"heading": {"en": "Discussion", "ja": "考察"}, "body": {"en": "", "ja": ""}},
        {"heading": {"en": "Conclusion", "ja": "結論"}, "body": {"en": "", "ja": ""}},
    ],
    "references": [],
}

TEMPLATES: dict[str, dict] = {
    "default": DEFAULT_SPEC,
    "short": {
        "title": {"en": "Untitled Paper", "ja": "無題の論文"},
        "authors": [],
        "abstract": {"en": "", "ja": ""},
        "sections": [
            {"heading": {"en": "Introduction", "ja": "はじめに"}, "body": {"en": "", "ja": ""}},
            {"heading": {"en": "Results & Discussion", "ja": "結果と考察"}, "body": {"en": "", "ja": ""}},
            {"heading": {"en": "Conclusion", "ja": "結論"}, "body": {"en": "", "ja": ""}},
        ],
        "references": [],
    },
    "review": {
        "title": {"en": "Untitled Review", "ja": "無題のレビュー"},
        "authors": [],
        "abstract": {"en": "", "ja": ""},
        "sections": [
            {"heading": {"en": "Introduction", "ja": "はじめに"}, "body": {"en": "", "ja": ""}},
            {"heading": {"en": "Background", "ja": "背景"}, "body": {"en": "", "ja": ""}},
            {"heading": {"en": "Current State of Research", "ja": "研究の現状"}, "body": {"en": "", "ja": ""}},
            {"heading": {"en": "Future Directions", "ja": "今後の方向性"}, "body": {"en": "", "ja": ""}},
            {"heading": {"en": "Conclusion", "ja": "結論"}, "body": {"en": "", "ja": ""}},
        ],
        "references": [],
    },
}

# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------
MD_EXTENSIONS = [
    "tables",
    "fenced_code",
    "footnotes",
    "toc",
    "smarty",
]


def _render_markdown(text: str) -> str:
    """Convert Markdown text to HTML."""
    return markdown.markdown(text, extensions=MD_EXTENSIONS)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _projects_dir() -> Path:
    d = Path(os.environ.get("PAPERCLAW_PROJECTS_DIR", DEFAULT_PROJECTS_DIR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _project_path(name: str) -> Path:
    return _projects_dir() / name


def _spec_path(name: str) -> Path:
    return _project_path(name) / "paper_spec.yaml"


def _load_spec(name: str) -> dict:
    p = _spec_path(name)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_spec(name: str, spec: dict) -> None:
    p = _spec_path(name)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _list_projects() -> list[str]:
    d = _projects_dir()
    if not d.exists():
        return []
    return sorted(
        [p.name for p in d.iterdir() if p.is_dir() and (p / "paper_spec.yaml").exists()]
    )


def _normalize_spec(spec: dict) -> dict:
    """Normalize spec to the format expected by PDFBuilder.

    The web editor may store data with 'title' at top level and 'body' for sections,
    while PDFBuilder expects 'meta.title' and 'content' for sections.
    """
    out = dict(spec)

    # Ensure meta block exists
    if "meta" not in out:
        out["meta"] = {}
    meta = out["meta"]

    # title
    if "title" in out and "title" not in meta:
        meta["title"] = out["title"]
    if "title" not in meta:
        meta["title"] = {"en": "Untitled", "ja": "無題"}

    # template
    if "template" not in meta:
        meta["template"] = "twocol"

    # keywords: support comma-separated string
    kw = out.get("keywords", meta.get("keywords", {}))
    if isinstance(kw, str):
        kw = {"en": kw, "ja": kw}
    meta["keywords"] = kw

    # authors: normalize list of strings to list of dicts
    authors = out.get("authors", meta.get("authors", []))
    normalized_authors = []
    for a in authors:
        if isinstance(a, str):
            normalized_authors.append({"name": a, "affiliation": ""})
        elif isinstance(a, dict):
            normalized_authors.append(a)
    out["authors"] = normalized_authors
    meta["authors"] = normalized_authors

    # sections: normalize 'body' to 'content'
    for sec in out.get("sections", []):
        if "body" in sec and "content" not in sec:
            sec["content"] = sec.pop("body")
        for sub in sec.get("subsections", []):
            if "body" in sub and "content" not in sub:
                sub["content"] = sub.pop("body")

    # references: normalize list of strings to structured
    refs = out.get("references", [])
    if refs and isinstance(refs[0], str):
        # Keep as strings for rendering
        pass

    out["meta"] = meta
    return out


def _render_preview(spec: dict, lang: str = "en") -> str:
    """Render a paper spec to an HTML preview."""
    parts: list[str] = []

    title = spec.get("title", {})
    title_text = title.get(lang, title.get("en", "Untitled"))
    parts.append(f"<h1 class='paper-title'>{title_text}</h1>")

    authors = spec.get("authors", [])
    if authors:
        parts.append("<p class='paper-authors'>" + ", ".join(authors) + "</p>")

    abstract = spec.get("abstract", {})
    abstract_text = abstract.get(lang, abstract.get("en", ""))
    if abstract_text.strip():
        parts.append("<div class='paper-abstract'>")
        parts.append(f"<h2>{'Abstract' if lang == 'en' else '要旨'}</h2>")
        parts.append(_render_markdown(abstract_text))
        parts.append("</div>")

    for section in spec.get("sections", []):
        heading = section.get("heading", {})
        heading_text = heading.get(lang, heading.get("en", "")) if isinstance(heading, dict) else str(heading)
        body = section.get("content", section.get("body", {}))
        if isinstance(body, dict):
            body_text = body.get(lang, body.get("en", ""))
        else:
            body_text = str(body)
        parts.append(f"<h2>{heading_text}</h2>")
        if body_text.strip():
            parts.append(_render_markdown(body_text))

        # Render subsections
        for sub in section.get("subsections", []):
            sub_h = sub.get("heading", {})
            sub_heading = sub_h.get(lang, sub_h.get("en", "")) if isinstance(sub_h, dict) else str(sub_h)
            sub_body = sub.get("content", sub.get("body", {}))
            if isinstance(sub_body, dict):
                sub_text = sub_body.get(lang, sub_body.get("en", ""))
            else:
                sub_text = str(sub_body)
            parts.append(f"<h3>{sub_heading}</h3>")
            if sub_text.strip():
                parts.append(_render_markdown(sub_text))

    references = spec.get("references", [])
    if references:
        parts.append(f"<h2>{'References' if lang == 'en' else '参考文献'}</h2>")
        parts.append("<ol class='paper-references'>")
        for ref in references:
            parts.append(f"<li>{ref}</li>")
        parts.append("</ol>")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Flask app factory
# ---------------------------------------------------------------------------

def create_app(projects_dir: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["SECRET_KEY"] = os.environ.get("PAPERCLAW_SECRET", "paperclaw-dev-key")

    if projects_dir:
        os.environ["PAPERCLAW_PROJECTS_DIR"] = projects_dir

    # ------------------------------------------------------------------
    # Page routes
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        projects = _list_projects()
        templates = list(TEMPLATES.keys())
        return render_template("index.html", projects=projects, templates=templates)

    @app.route("/project/<name>")
    def editor(name: str):
        proj = _project_path(name)
        if not proj.exists():
            return render_template("index.html", projects=_list_projects(),
                                   templates=list(TEMPLATES.keys()),
                                   error=f"Project '{name}' not found."), 404
        spec = _load_spec(name)
        return render_template("editor.html", project_name=name, spec=spec)

    # ------------------------------------------------------------------
    # API routes
    # ------------------------------------------------------------------

    @app.route("/api/project", methods=["POST"])
    def api_create_project():
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Project name is required."}), 400

        # Sanitise name
        safe_name = "".join(c if (c.isalnum() or c in "-_") else "_" for c in name)
        proj = _project_path(safe_name)
        if proj.exists():
            return jsonify({"error": f"Project '{safe_name}' already exists."}), 409

        template_key = data.get("template", "default")
        spec = json.loads(json.dumps(TEMPLATES.get(template_key, DEFAULT_SPEC)))

        lang = data.get("language", "en")
        if lang not in ("en", "ja"):
            lang = "en"

        proj.mkdir(parents=True, exist_ok=True)
        (proj / "figures").mkdir(exist_ok=True)
        (proj / "output").mkdir(exist_ok=True)

        _save_spec(safe_name, spec)
        return jsonify({"name": safe_name, "url": f"/project/{safe_name}"}), 201

    @app.route("/api/project/<name>/spec", methods=["GET"])
    def api_get_spec(name: str):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404
        spec = _load_spec(name)
        return jsonify(spec)

    @app.route("/api/project/<name>/spec", methods=["POST"])
    def api_save_spec(name: str):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404
        data = request.get_json(force=True)
        _save_spec(name, data)
        return jsonify({"status": "saved"})

    @app.route("/api/project/<name>/section/<int:idx>", methods=["POST"])
    def api_update_section(name: str, idx: int):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404
        spec = _load_spec(name)
        sections = spec.get("sections", [])
        if idx < 0 or idx >= len(sections):
            return jsonify({"error": f"Section index {idx} out of range."}), 400
        data = request.get_json(force=True)
        if "heading" in data:
            sections[idx]["heading"] = data["heading"]
        if "body" in data:
            sections[idx]["body"] = data["body"]
        spec["sections"] = sections
        _save_spec(name, spec)
        return jsonify({"status": "saved", "index": idx})

    @app.route("/api/project/<name>/build", methods=["POST"])
    def api_build(name: str):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404

        spec = _load_spec(name)
        data = request.get_json(silent=True) or {}
        lang = data.get("language", "en")
        output_dir = _project_path(name) / "output"
        output_dir.mkdir(exist_ok=True)

        # Normalize spec to PDFBuilder format
        normalized = _normalize_spec(spec)
        pdf_filename = f"paper_{lang}.pdf"
        pdf_path = output_dir / pdf_filename

        try:
            from paperclaw.latex_builder import LaTeXBuilder
            builder = LaTeXBuilder()
            result = builder.build(normalized, str(pdf_path), language=lang)
            return jsonify({"status": "built", "path": result})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/project/<name>/preview", methods=["GET"])
    def api_preview(name: str):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404
        spec = _load_spec(name)
        lang = request.args.get("lang", "en")
        normalized = _normalize_spec(spec)

        # Try PDFBuilder for richer preview
        try:
            from paperclaw.pdf_builder import PDFBuilder
            builder = PDFBuilder()
            # Use the body content from the full HTML (strip <html>/<head> wrapper)
            full_html = builder.preview_html(normalized, language=lang)
            # Extract body content for embedding in editor
            import re
            body_match = re.search(r'<body>(.*)</body>', full_html, re.DOTALL)
            if body_match:
                html = body_match.group(1)
            else:
                html = full_html
        except Exception:
            html = _render_preview(spec, lang)

        return jsonify({"html": html, "lang": lang})

    @app.route("/api/project/<name>/pdf/<lang>", methods=["GET"])
    def api_download_pdf(name: str, lang: str):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404
        pdf_path = _project_path(name) / "output" / f"paper_{lang}.pdf"
        if not pdf_path.exists():
            # Try HTML fallback
            html_path = _project_path(name) / "output" / f"paper_{lang}.html"
            if html_path.exists():
                return send_file(str(html_path), as_attachment=True,
                                 download_name=f"paper_{lang}.html")
            return jsonify({"error": "PDF not found. Build first."}), 404
        return send_file(str(pdf_path), as_attachment=True,
                         download_name=f"paper_{lang}.pdf")

    @app.route("/api/project/<name>/figures", methods=["POST"])
    def api_figures(name: str):
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404

        figures_dir = _project_path(name) / "figures"
        figures_dir.mkdir(exist_ok=True)
        saved: list[str] = []

        if request.files:
            for key, f in request.files.items():
                if f.filename:
                    safe = "".join(
                        c if (c.isalnum() or c in "-_.") else "_" for c in f.filename
                    )
                    dest = figures_dir / safe
                    f.save(str(dest))
                    saved.append(safe)

        return jsonify({"status": "uploaded", "files": saved})

    @app.route("/api/project/<name>/diagrams", methods=["GET"])
    def api_list_diagrams(name: str):
        """List diagrams (mermaid sources and rendered PNGs) in a project."""
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404

        figures_dir = _project_path(name) / "figures"
        diagrams = []
        if figures_dir.exists():
            for mmd in sorted(figures_dir.glob("*.mmd")):
                fig_id = mmd.stem
                png_exists = (figures_dir / f"{fig_id}.png").exists()
                mermaid_src = mmd.read_text(encoding="utf-8")
                diagrams.append({
                    "id": fig_id,
                    "mermaid": mermaid_src,
                    "png": f"/api/project/{name}/figure/{fig_id}.png" if png_exists else None,
                })
        return jsonify({"diagrams": diagrams})

    @app.route("/api/project/<name>/figure/<path:filename>", methods=["GET"])
    def api_get_figure(name: str, filename: str):
        """Serve a figure file."""
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404
        fig_path = _project_path(name) / "figures" / filename
        if not fig_path.exists():
            return jsonify({"error": "Figure not found."}), 404
        return send_file(str(fig_path))

    @app.route("/api/project/<name>/data", methods=["POST"])
    def api_upload_data(name: str):
        """Upload data files to a project's data/ directory."""
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404

        data_dir = _project_path(name) / "data"
        data_dir.mkdir(exist_ok=True)
        saved: list[str] = []

        if request.files:
            for key, f in request.files.items():
                if f.filename:
                    safe = "".join(
                        c if (c.isalnum() or c in "-_.") else "_" for c in f.filename
                    )
                    dest = data_dir / safe
                    f.save(str(dest))
                    saved.append(safe)

        return jsonify({"status": "uploaded", "files": saved})

    @app.route("/api/project/<name>/generate", methods=["POST"])
    def api_generate(name: str):
        """Auto-generate paper content using AI.

        Supports two modes:
        1. Overview + data files (existing flow)
        2. Experiment directory (new forge flow)
        """
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404

        data = request.get_json(force=True)
        overview = data.get("overview", "").strip()
        experiment_dir = data.get("experiment_dir", "").strip()

        proj = _project_path(name)
        api_key = data.get("api_key") or os.environ.get("AZURE_OPENAI_API_KEY", "")
        endpoint = data.get("endpoint") or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        deployment = data.get("deployment") or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "")
        title_en = data.get("title_en", "Untitled Paper")
        title_ja = data.get("title_ja", "無題の論文")
        template = data.get("template", "twocol")

        try:
            from paperclaw.pipeline import Pipeline
            pipeline = Pipeline(str(proj))

            if experiment_dir:
                # ── Forge mode: scan experiment directory ──
                exp_path = Path(experiment_dir).expanduser().resolve()
                if not exp_path.exists():
                    return jsonify({"error": f"Experiment directory not found: {experiment_dir}"}), 400

                # Collect extra uploaded docs
                extra_docs_dir = proj / "extra_docs"
                extra_doc_paths = []
                if extra_docs_dir.exists():
                    for f in extra_docs_dir.iterdir():
                        if f.is_file():
                            extra_doc_paths.append(str(f))

                spec = pipeline.forge(
                    experiment_dir=str(exp_path),
                    extra_docs=extra_doc_paths or None,
                    overview=overview,
                    api_key=api_key,
                    endpoint=endpoint,
                    deployment=deployment,
                    language="both",
                    title_en=title_en,
                    title_ja=title_ja,
                    template=template,
                    build=False,
                )
            else:
                # ── Legacy mode: overview + uploaded data files ──
                if not overview:
                    return jsonify({"error": "Research overview or experiment directory is required."}), 400

                data_files = data.get("data_files", [])
                resolved_paths = []
                for df in data_files:
                    p = proj / df
                    if p.exists():
                        resolved_paths.append(str(p))

                spec = pipeline.auto_generate(
                    overview=overview,
                    data_paths=resolved_paths or None,
                    api_key=api_key,
                    endpoint=endpoint,
                    deployment=deployment,
                    language="both",
                    title_en=title_en,
                    title_ja=title_ja,
                    template=template,
                    build=False,
                )

            saved = _load_spec(name)
            return jsonify({"status": "generated", "spec": saved})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/project/<name>/extra_docs", methods=["POST"])
    def api_upload_extra_docs(name: str):
        """Upload extra documents (Word/PDF/MD) for context."""
        if not _project_path(name).exists():
            return jsonify({"error": "Project not found."}), 404

        docs_dir = _project_path(name) / "extra_docs"
        docs_dir.mkdir(exist_ok=True)
        saved: list[str] = []

        if request.files:
            for key, f in request.files.items():
                if f.filename:
                    safe = "".join(
                        c if (c.isalnum() or c in "-_.") else "_" for c in f.filename
                    )
                    dest = docs_dir / safe
                    f.save(str(dest))
                    saved.append(safe)

        return jsonify({"status": "uploaded", "files": saved})

    return app


# ---------------------------------------------------------------------------
# Full HTML builder (for PDF generation fallback)
# ---------------------------------------------------------------------------

def _build_full_html(spec: dict, lang: str = "en") -> str:
    """Build a complete standalone HTML document for a paper."""
    title = spec.get("title", {}).get(lang, "Paper")
    body = _render_preview(spec, lang)
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 2.5cm; }}
  body {{ font-family: 'Times New Roman', 'Noto Serif JP', serif;
         font-size: 11pt; line-height: 1.6; color: #222; max-width: 700px;
         margin: 0 auto; padding: 2rem; }}
  h1 {{ font-size: 16pt; text-align: center; margin-bottom: 0.3em; }}
  h2 {{ font-size: 13pt; margin-top: 1.5em; border-bottom: 1px solid #ccc;
       padding-bottom: 0.2em; }}
  .paper-authors {{ text-align: center; color: #555; }}
  .paper-abstract {{ background: #f9f9f9; padding: 1em; border-left: 3px solid #2166AC;
                     margin: 1em 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ccc; padding: 0.4em 0.8em; text-align: left; }}
  th {{ background: #f0f0f0; }}
  code {{ background: #f4f4f4; padding: 0.15em 0.3em; border-radius: 3px;
         font-size: 0.9em; }}
  pre code {{ display: block; padding: 1em; overflow-x: auto; }}
  .paper-references li {{ margin-bottom: 0.4em; }}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the development server."""
    import argparse

    parser = argparse.ArgumentParser(description="PaperClaw editor server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--projects-dir", default=None,
                        help="Directory to store projects")
    args = parser.parse_args()

    app = create_app(projects_dir=args.projects_dir)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
