"""CLI for PaperForge - paper-forge command."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """PaperForge - Research data to academic paper PDF generator."""
    pass


@cli.command()
@click.argument("project_dir")
@click.option("--title-en", default="", help="Paper title in English")
@click.option("--title-ja", default="", help="Paper title in Japanese")
@click.option("--template", default="twocol",
              type=click.Choice(["twocol", "onecol", "nature", "ieee"]),
              help="Paper template style")
@click.option("--author", multiple=True, help="Author name (can specify multiple)")
@click.option("--affiliation", multiple=True, help="Author affiliation (matches --author order)")
def init(project_dir, title_en, title_ja, template, author, affiliation):
    """Initialize a new paper project.

    Creates PROJECT_DIR with paper_spec.yaml and directory structure.
    """
    from .pipeline import Pipeline

    pipeline = Pipeline(project_dir)

    authors = []
    for i, name in enumerate(author):
        aff = affiliation[i] if i < len(affiliation) else ""
        authors.append({"name": name, "affiliation": aff})

    spec = pipeline.init_project(
        title_en=title_en or "Untitled Paper",
        title_ja=title_ja or "",
        template=template,
        authors=authors or None,
    )

    click.echo(f"Project initialized: {project_dir}")
    click.echo(f"  paper_spec.yaml created")
    click.echo(f"  Template: {template}")
    click.echo(f"  Edit paper_spec.yaml to add your content, then run:")
    click.echo(f"    paper-forge build {project_dir}")


@cli.command()
@click.argument("project_dir")
@click.option("--lang", default="all", type=click.Choice(["en", "ja", "all"]),
              help="Language to build")
def build(project_dir, lang):
    """Build PDF from paper specification.

    Reads paper_spec.yaml from PROJECT_DIR and generates PDF(s).
    """
    from .pipeline import Pipeline

    pipeline = Pipeline(project_dir)

    if lang == "all":
        click.echo("Building PDFs for all languages...")
        results = pipeline.build_all()
        for language, path in results.items():
            if path.startswith("Error"):
                click.echo(f"  [{language}] {path}", err=True)
            else:
                click.echo(f"  [{language}] {path}")
    else:
        click.echo(f"Building {lang} PDF...")
        path = pipeline.build_pdf(lang)
        click.echo(f"  {path}")


@cli.command()
@click.argument("project_dir")
@click.option("--lang", default="en", type=click.Choice(["en", "ja"]),
              help="Preview language")
@click.option("--output", default=None, help="Save HTML to file")
def preview(project_dir, lang, output):
    """Generate HTML preview of the paper."""
    from .pipeline import Pipeline

    pipeline = Pipeline(project_dir)
    html = pipeline.preview_html(lang)

    if output:
        Path(output).write_text(html, encoding="utf-8")
        click.echo(f"Preview saved to {output}")
    else:
        click.echo(html)


@cli.command()
@click.argument("data_path")
@click.option("--output", default=None, help="Save analysis to JSON file")
def analyze(data_path, output):
    """Analyze research data file (CSV, JSON, YAML).

    Shows data summary and suggests figure types.
    """
    from .pipeline import Pipeline

    pipeline = Pipeline(".")
    result = pipeline.analyze_data(data_path)

    formatted = json.dumps(result, indent=2, ensure_ascii=False)

    if output:
        Path(output).write_text(formatted, encoding="utf-8")
        click.echo(f"Analysis saved to {output}")
    else:
        click.echo(formatted)


@cli.command()
@click.argument("project_dir")
@click.option("--spec", default=None, help="Figure specifications JSON file")
def figures(project_dir, spec):
    """Generate figures from specifications."""
    from .pipeline import Pipeline

    pipeline = Pipeline(project_dir)

    figure_specs = None
    if spec:
        with open(spec, "r") as f:
            figure_specs = json.load(f)

    results = pipeline.generate_figures(figure_specs)
    for path in results:
        click.echo(f"  Generated: {path}")


@cli.command()
@click.argument("project_dir", default=".")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, help="Port to listen on")
@click.option("--debug/--no-debug", default=True, help="Enable debug mode")
def edit(project_dir, host, port, debug):
    """Launch interactive web editor.

    Opens a browser-based editor for paper_spec.yaml with live preview.
    """
    from .web.app import create_app

    app = create_app(projects_dir=project_dir)
    click.echo(f"Starting PaperForge editor at http://{host}:{port}")
    click.echo(f"Projects directory: {project_dir}")
    click.echo("Press Ctrl+C to stop.")
    app.run(host=host, port=port, debug=debug)


@cli.command()
@click.argument("project_dir")
def status(project_dir):
    """Show project status and paper summary."""
    from .pipeline import Pipeline

    pipeline = Pipeline(project_dir)

    try:
        spec = pipeline.load_spec()
    except FileNotFoundError:
        click.echo(f"No project found at {project_dir}", err=True)
        sys.exit(1)

    d = spec.to_dict()
    title = d.get("meta", {}).get("title", {})

    click.echo(f"Project: {project_dir}")
    click.echo(f"  Title (EN): {title.get('en', 'N/A')}")
    click.echo(f"  Title (JA): {title.get('ja', 'N/A')}")
    click.echo(f"  Template: {d.get('meta', {}).get('template', 'N/A')}")
    click.echo(f"  Authors: {len(d.get('authors', []))}")
    click.echo(f"  Sections: {len(d.get('sections', []))}")
    click.echo(f"  Figures: {len(d.get('figures', {}))}")
    click.echo(f"  Tables: {len(d.get('tables', {}))}")
    click.echo(f"  References: {len(d.get('references', []))}")

    # Check outputs
    output_dir = Path(project_dir) / "output"
    if output_dir.exists():
        pdfs = list(output_dir.glob("*.pdf"))
        if pdfs:
            click.echo(f"  Built PDFs:")
            for pdf in pdfs:
                size_kb = pdf.stat().st_size / 1024
                click.echo(f"    {pdf.name} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    cli()
