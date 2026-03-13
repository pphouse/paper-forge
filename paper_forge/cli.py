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
@click.argument("experiment_dir")
@click.option("--project-dir", "-o", default=None,
              help="Output project directory (default: experiment_dir + '_paper')")
@click.option("--doc", "extra_docs", multiple=True,
              help="Extra document (Word/PDF/MD) to include as context. Can repeat.")
@click.option("--overview", default="",
              help="Research overview text or path to .txt file (auto-derived if omitted)")
@click.option("--api-key", default=None, envvar="AZURE_OPENAI_API_KEY",
              help="Azure OpenAI API key")
@click.option("--endpoint", default=None, envvar="AZURE_OPENAI_ENDPOINT",
              help="Azure OpenAI endpoint URL")
@click.option("--deployment", default=None, envvar="AZURE_OPENAI_DEPLOYMENT",
              help="Azure OpenAI deployment name")
@click.option("--lang", default="both",
              type=click.Choice(["en", "ja", "both"]),
              help="Language for generation")
@click.option("--title-en", default="", help="Paper title (EN). Auto-derived if empty.")
@click.option("--title-ja", default="", help="Paper title (JA). Auto-derived if empty.")
@click.option("--template", default="twocol",
              type=click.Choice(["twocol", "onecol", "nature", "ieee"]),
              help="Paper template")
@click.option("--author", multiple=True, help="Author name")
@click.option("--affiliation", multiple=True, help="Author affiliation")
@click.option("--no-build", is_flag=True, default=False,
              help="Skip PDF building")
def forge(experiment_dir, project_dir, extra_docs, overview, api_key, endpoint,
          deployment, lang, title_en, title_ja, template, author, affiliation, no_build):
    """Fully automated: experiment directory -> paper PDF.

    Scans EXPERIMENT_DIR for data files, images, logs, and documents.
    Optionally adds external docs (--doc report.docx --doc notes.pdf).
    AI generates the full paper and builds PDF.

    Examples:

    \b
      paper-forge forge ./experiments/
      paper-forge forge ./experiments/ --doc report.docx --doc notes.pdf
      paper-forge forge ./experiments/ --title-en "Effect of X" --author "Alice"
      paper-forge forge ./experiments/ --overview overview.txt
    """
    from .pipeline import Pipeline

    exp_path = Path(experiment_dir).resolve()
    if not exp_path.exists():
        click.echo(f"Error: experiment directory not found: {experiment_dir}", err=True)
        sys.exit(1)

    if not project_dir:
        project_dir = str(exp_path.parent / (exp_path.name + "_paper"))

    authors = []
    for i, name in enumerate(author):
        aff = affiliation[i] if i < len(affiliation) else ""
        authors.append({"name": name, "affiliation": aff})

    pipeline = Pipeline(project_dir)

    click.echo(f"Experiment directory: {experiment_dir}")
    click.echo(f"Output project:      {project_dir}")
    if extra_docs:
        click.echo(f"Extra documents:     {', '.join(extra_docs)}")
    click.echo("")

    click.echo("Stage 1: Scanning experiment directory...")
    click.echo("Stage 2: Analyzing data files...")
    click.echo("Stage 3: Generating paper via Azure OpenAI...")

    try:
        spec = pipeline.forge(
            experiment_dir=experiment_dir,
            extra_docs=list(extra_docs) if extra_docs else None,
            overview=overview,
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            language=lang,
            title_en=title_en,
            title_ja=title_ja,
            template=template,
            authors=authors or None,
            build=not no_build,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"\nPaper spec saved: {pipeline.spec_path}")

    if not no_build:
        click.echo("Stage 4: Building PDF...")
        output_dir = Path(project_dir) / "output"
        if output_dir.exists():
            for pdf in output_dir.glob("*.pdf"):
                size_kb = pdf.stat().st_size / 1024
                click.echo(f"  {pdf.name} ({size_kb:.0f} KB)")

    click.echo("\nDone!")


@cli.command()
@click.argument("project_dir")
@click.option("--overview", required=True,
              help="Research overview text, or path to a .txt file")
@click.option("--data", "data_paths", multiple=True,
              help="Path to data file (CSV/JSON). Can specify multiple.")
@click.option("--api-key", default=None, envvar="AZURE_OPENAI_API_KEY",
              help="Azure OpenAI API key")
@click.option("--endpoint", default=None, envvar="AZURE_OPENAI_ENDPOINT",
              help="Azure OpenAI endpoint URL")
@click.option("--deployment", default=None, envvar="AZURE_OPENAI_DEPLOYMENT",
              help="Azure OpenAI deployment name")
@click.option("--lang", default="both",
              type=click.Choice(["en", "ja", "both"]),
              help="Language for generation")
@click.option("--title-en", default="", help="Paper title in English")
@click.option("--title-ja", default="", help="Paper title in Japanese")
@click.option("--template", default="twocol",
              type=click.Choice(["twocol", "onecol", "nature", "ieee"]),
              help="Paper template")
@click.option("--author", multiple=True, help="Author name")
@click.option("--affiliation", multiple=True, help="Author affiliation")
@click.option("--no-build", is_flag=True, default=False,
              help="Skip PDF building (generate spec only)")
def generate(project_dir, overview, data_paths, api_key, endpoint, deployment,
             lang, title_en, title_ja, template, author, affiliation, no_build):
    """Auto-generate a paper from data + research overview using Azure OpenAI.

    Example:
        paper-forge generate ./my-project \\
            --overview "We studied the effect of X on Y..." \\
            --data results.csv \\
            --title-en "Effect of X on Y" \\
            --author "Alice Smith" --affiliation "MIT"
    """
    from .pipeline import Pipeline

    authors = []
    for i, name in enumerate(author):
        aff = affiliation[i] if i < len(affiliation) else ""
        authors.append({"name": name, "affiliation": aff})

    pipeline = Pipeline(project_dir)

    click.echo("Stage 1: Analyzing data...")
    click.echo("Stage 2: Generating paper via Azure OpenAI API...")

    try:
        spec = pipeline.auto_generate(
            overview=overview,
            data_paths=list(data_paths) if data_paths else None,
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            language=lang,
            title_en=title_en or "Untitled Paper",
            title_ja=title_ja or "無題の論文",
            template=template,
            authors=authors or None,
            build=not no_build,
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Paper spec saved: {pipeline.spec_path}")

    if not no_build:
        click.echo("Stage 3: Building PDF...")
        output_dir = Path(project_dir) / "output"
        if output_dir.exists():
            for pdf in output_dir.glob("*.pdf"):
                size_kb = pdf.stat().st_size / 1024
                click.echo(f"  {pdf.name} ({size_kb:.0f} KB)")

    click.echo("Done!")


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
