"""CLI for PaperClaw - paperclaw command."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
import yaml


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """PaperClaw - Research data to academic paper PDF generator."""
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
    click.echo(f"    paperclaw build {project_dir}")


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
      paperclaw forge ./experiments/
      paperclaw forge ./experiments/ --doc report.docx --doc notes.pdf
      paperclaw forge ./experiments/ --title-en "Effect of X" --author "Alice"
      paperclaw forge ./experiments/ --overview overview.txt
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
        paperclaw generate ./my-project \\
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
    click.echo(f"Starting PaperClaw editor at http://{host}:{port}")
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


# ============================================================================
# Quality Assurance Agent Commands
# ============================================================================

@cli.command("check-citations")
@click.argument("project_dir")
@click.option("--fix", is_flag=True, help="Auto-fix mismatched citations")
@click.option("--output", default=None, help="Save report to JSON file")
def check_citations(project_dir, fix, output):
    """Check references for hallucinations using Semantic Scholar API.

    Verifies that all cited papers actually exist and have correct metadata.
    """
    from .pipeline import Pipeline
    from .agents import CitationChecker

    pipeline = Pipeline(project_dir)
    spec = pipeline.load_spec()

    click.echo("Checking citations against Semantic Scholar...")
    checker = CitationChecker()

    if fix:
        report, corrected_spec = checker.check_and_fix(spec.to_dict())
        # Save corrected spec
        pipeline.save_spec(corrected_spec)
        click.echo(f"Corrected spec saved to {pipeline.spec_path}")
    else:
        report = checker.check_references(spec.to_dict())

    click.echo(f"\nResults:")
    click.echo(f"  Total references: {report.total_references}")
    click.echo(f"  Verified: {report.verified}")
    click.echo(f"  Not found: {report.not_found}")
    click.echo(f"  Mismatched: {report.mismatched}")
    click.echo(f"  Verification rate: {report.verification_rate:.1%}")

    if report.not_found > 0 or report.mismatched > 0:
        click.echo("\nIssues:")
        for result in report.results:
            if result.status != "verified":
                icon = "❌" if result.status == "not_found" else "⚠️"
                click.echo(f"  {icon} [{result.key}] {result.message}")
                if result.suggested_correction:
                    click.echo(f"      Suggestion: {result.suggested_correction.get('title', '')}")

    if output:
        Path(output).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        click.echo(f"\nReport saved to {output}")


@cli.command("find-literature")
@click.argument("query")
@click.option("--sources", default="arxiv,semantic_scholar",
              help="Comma-separated sources: arxiv,biorxiv,semantic_scholar")
@click.option("--max-results", default=20, help="Maximum results per source")
@click.option("--output", default=None, help="Save results to JSON file")
@click.option("--add-to", default=None, help="Add top results to project's references")
def find_literature(query, sources, max_results, output, add_to):
    """Search for related literature on arxiv, biorxiv, and Semantic Scholar.

    Example:
        paperclaw find-literature "attention mechanism medical imaging"
        paperclaw find-literature "deep learning chest x-ray" --add-to ./project
    """
    from .agents import LiteratureAgent

    click.echo(f"Searching for: {query}")
    click.echo(f"Sources: {sources}")

    agent = LiteratureAgent()
    source_list = [s.strip() for s in sources.split(",")]
    report = agent.search(query, sources=source_list, max_results_per_source=max_results)

    click.echo(f"\nFound {report.total_found} papers:")
    for i, paper in enumerate(report.papers[:10], 1):
        click.echo(f"  {i}. [{paper.source}] {paper.title[:60]}...")
        click.echo(f"     {', '.join(paper.authors[:2])} ({paper.year})")
        if paper.citation_count > 0:
            click.echo(f"     Citations: {paper.citation_count}")

    if output:
        Path(output).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        click.echo(f"\nResults saved to {output}")

    if add_to:
        from .pipeline import Pipeline
        pipeline = Pipeline(add_to)
        spec = pipeline.load_spec()
        spec_dict = spec.to_dict()

        new_refs = report.get_suggested_references(5)
        existing_refs = spec_dict.get("references", [])
        spec_dict["references"] = existing_refs + new_refs

        pipeline.save_spec(spec_dict)
        click.echo(f"\nAdded {len(new_refs)} references to {add_to}")


@cli.command("check-figures")
@click.argument("project_dir")
@click.option("--output", default=None, help="Save report to JSON file")
def check_figures(project_dir, output):
    """Check figure quality: resolution, text overlap, consistency.

    Analyzes all figures in the project for potential issues.
    """
    from .pipeline import Pipeline
    from .agents import FigureChecker

    pipeline = Pipeline(project_dir)
    spec = pipeline.load_spec()

    click.echo("Checking figure quality...")
    checker = FigureChecker(use_ocr=True)
    report = checker.check_figures(spec.to_dict(), project_dir)

    click.echo(f"\nResults:")
    click.echo(f"  Total figures: {report.total_figures}")
    click.echo(f"  OK: {report.ok}")
    click.echo(f"  With errors: {report.with_errors}")
    click.echo(f"  With warnings: {report.with_warnings}")

    if report.with_errors > 0 or report.with_warnings > 0:
        click.echo("\nIssues:")
        for result in report.results:
            if result.issues:
                click.echo(f"\n  {result.figure_id}:")
                for issue in result.issues:
                    icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
                    click.echo(f"    {icon} {issue.message}")

    suggestions = checker.suggest_improvements(report)
    if suggestions:
        click.echo("\nSuggestions:")
        for s in suggestions[:5]:
            click.echo(f"  • {s}")

    if output:
        Path(output).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        click.echo(f"\nReport saved to {output}")


@cli.command("review-structure")
@click.argument("project_dir")
@click.option("--lang", default="en", type=click.Choice(["en", "ja"]),
              help="Language to analyze")
@click.option("--output", default=None, help="Save report to JSON file")
def review_structure(project_dir, lang, output):
    """Review paper structure: section flow, balance, missing elements.

    Analyzes the logical structure and provides improvement suggestions.
    """
    from .pipeline import Pipeline
    from .agents import StructureReviewer

    pipeline = Pipeline(project_dir)
    spec = pipeline.load_spec()

    click.echo("Analyzing paper structure...")
    reviewer = StructureReviewer(language=lang)
    report = reviewer.analyze(spec.to_dict())

    click.echo(f"\nStructure Score: {report.overall_score:.0f}/100")
    click.echo(f"Total word count: {report.total_word_count}")
    click.echo(f"Sections: {report.total_sections}")
    click.echo(f"Section order correct: {'Yes' if report.section_order_correct else 'No'}")

    click.echo("\nDetected sections:")
    for section_type, present in report.detected_sections.items():
        icon = "✓" if present else "✗"
        click.echo(f"  {icon} {section_type}")

    if report.issues:
        click.echo("\nIssues:")
        for issue in report.issues:
            icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
            click.echo(f"  {icon} {issue.message}")
            if issue.suggestion:
                click.echo(f"      → {issue.suggestion}")

    if output:
        Path(output).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        click.echo(f"\nReport saved to {output}")


@cli.command("review-content")
@click.argument("project_dir")
@click.option("--lang", default="ja", type=click.Choice(["en", "ja"]),
              help="Language for analysis output")
@click.option("--no-llm", is_flag=True, help="Skip LLM analysis (rule-based only)")
@click.option("--output", default=None, help="Save report to JSON file")
def review_content(project_dir, lang, no_llm, output):
    """Review paper content for logical consistency using LLM.

    Analyzes claim-evidence alignment, cross-section consistency,
    and argumentation flow.
    """
    from .pipeline import Pipeline
    from .agents import ContentReviewer

    pipeline = Pipeline(project_dir)
    spec = pipeline.load_spec()

    click.echo("論文内容を分析中..." if lang == "ja" else "Analyzing paper content...")
    reviewer = ContentReviewer(use_llm=not no_llm, language=lang)
    report = reviewer.review(spec.to_dict())

    click.echo(f"\n論理的一貫性スコア: {report.overall_coherence_score:.0f}/100")
    click.echo(f"分析セクション数: {report.sections_reviewed}")

    if report.summary:
        click.echo(f"\n要約: {report.summary}")

    if report.strengths:
        click.echo("\n強み:")
        for s in report.strengths:
            click.echo(f"  ✓ {s}")

    if report.weaknesses:
        click.echo("\n改善点:")
        for w in report.weaknesses:
            click.echo(f"  △ {w}")

    if report.issues:
        click.echo("\n検出された問題:")
        for issue in report.issues:
            icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
            click.echo(f"  {icon} [{issue.section}] {issue.message}")
            if issue.suggestion:
                click.echo(f"      → {issue.suggestion}")

    suggestions = reviewer.suggest_improvements(report)
    if suggestions:
        click.echo("\n改善提案:")
        for s in suggestions[:5]:
            click.echo(f"  • {s}")

    if output:
        Path(output).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        click.echo(f"\nレポートを保存しました: {output}")


@cli.command("qa")
@click.argument("project_dir")
@click.option("--full", is_flag=True, help="Include LLM-based content review")
@click.option("--output", default=None, help="Save full report to JSON file")
def qa(project_dir, full, output):
    """Run all quality assurance checks on the paper.

    Combines: citation check, figure check, structure review, and optionally content review.
    """
    from .pipeline import Pipeline
    from .agents import CitationChecker, FigureChecker, StructureReviewer, ContentReviewer

    pipeline = Pipeline(project_dir)
    spec = pipeline.load_spec()
    spec_dict = spec.to_dict()

    click.echo("=" * 60)
    click.echo("PaperClaw Quality Assurance Report")
    click.echo("=" * 60)

    full_report = {}

    # Structure review
    click.echo("\n1. Structure Review")
    click.echo("-" * 40)
    reviewer = StructureReviewer()
    structure_report = reviewer.analyze(spec_dict)
    click.echo(f"   Score: {structure_report.overall_score:.0f}/100")
    click.echo(f"   Issues: {len(structure_report.issues)}")
    full_report["structure"] = structure_report.to_dict()

    # Figure check
    click.echo("\n2. Figure Quality Check")
    click.echo("-" * 40)
    fig_checker = FigureChecker()
    fig_report = fig_checker.check_figures(spec_dict, project_dir)
    click.echo(f"   Checked: {fig_report.checked}")
    click.echo(f"   Issues: {fig_report.with_errors + fig_report.with_warnings}")
    full_report["figures"] = fig_report.to_dict()

    # Citation check
    click.echo("\n3. Citation Verification")
    click.echo("-" * 40)
    cit_checker = CitationChecker()
    cit_report = cit_checker.check_references(spec_dict)
    click.echo(f"   Verified: {cit_report.verified}/{cit_report.total_references}")
    click.echo(f"   Not found: {cit_report.not_found}")
    full_report["citations"] = cit_report.to_dict()

    # Content review (if --full flag)
    content_issues = 0
    if full:
        click.echo("\n4. Content Review (LLM)")
        click.echo("-" * 40)
        content_reviewer = ContentReviewer(use_llm=True)
        content_report = content_reviewer.review(spec_dict)
        click.echo(f"   Coherence score: {content_report.overall_coherence_score:.0f}/100")
        click.echo(f"   Issues: {len(content_report.issues)}")
        full_report["content"] = content_report.to_dict()
        content_issues = len(content_report.issues)

    # Overall summary
    total_issues = (
        len(structure_report.issues) +
        fig_report.with_errors + fig_report.with_warnings +
        cit_report.not_found + cit_report.mismatched +
        content_issues
    )

    click.echo("\n" + "=" * 60)
    click.echo("Summary")
    click.echo("=" * 60)
    click.echo(f"Structure score: {structure_report.overall_score:.0f}/100")
    click.echo(f"Citation verification: {cit_report.verification_rate:.1%}")
    if full and "content" in full_report:
        click.echo(f"Content coherence: {content_report.overall_coherence_score:.0f}/100")
    click.echo(f"Total issues found: {total_issues}")

    if total_issues == 0:
        click.echo("\n✓ Paper passed all quality checks!")
    else:
        click.echo(f"\n⚠ {total_issues} issues need attention")

    if output:
        Path(output).write_text(json.dumps(full_report, indent=2, ensure_ascii=False))
        click.echo(f"\nFull report saved to {output}")


@cli.command("auto-figures")
@click.argument("experiment_dir")
@click.option("--output", "-o", default=None, help="Output directory for figures")
def auto_figures(experiment_dir, output):
    """Automatically generate figures from experiment data.

    Scans EXPERIMENT_DIR for CSV/JSON files and generates appropriate
    visualizations (training curves, comparisons, confusion matrices, etc.)

    Example:
        paperclaw auto-figures ./my_experiment/
        paperclaw auto-figures ./my_experiment/ -o ./paper/figures/
    """
    from .auto_figure import AutoFigureGenerator

    click.echo(f"Scanning experiment directory: {experiment_dir}")

    generator = AutoFigureGenerator(experiment_dir, output)
    figures = generator.generate_all()

    if figures:
        click.echo(f"\nGenerated {len(figures)} figures:")
        for name, path in figures.items():
            click.echo(f"  {name}: {path}")
        click.echo(f"\nFigures saved to: {generator.output_dir}")
    else:
        click.echo("No suitable data found for figure generation.")


# ============================================================
# Skills System Commands
# ============================================================

@cli.group()
def skill():
    """Skills system for modular paper processing.

    Run individual skills or compose pipelines.
    """
    pass


@skill.command("list")
def skill_list():
    """List all available skills."""
    from .skills.registry import load_all_skills, list_skills

    load_all_skills()
    skills = list_skills()

    click.echo("Available Skills:")
    click.echo("-" * 60)

    for s in skills:
        click.echo(f"\n  {s['name']} (v{s['version']})")
        click.echo(f"    {s['description']}")
        if s['dependencies']:
            click.echo(f"    Dependencies: {', '.join(s['dependencies'])}")


@skill.command("run")
@click.argument("skill_name")
@click.argument("project_dir")
@click.option("--lang", default="en", type=click.Choice(["en", "ja"]),
              help="Target language")
@click.option("--config", "-c", multiple=True, help="Config key=value pairs")
@click.option("--output", "-o", default=None, help="Save result JSON to file")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def skill_run(skill_name, project_dir, lang, config, output, verbose):
    """Run a single skill.

    Examples:
        paperclaw skill run spec-parser ./my_paper/
        paperclaw skill run qa-citations ./my_paper/ -v
        paperclaw skill run auto-figure ./my_paper/ -c data_dir=experiments
    """
    from .skills.registry import load_all_skills, get_skill
    from .skills.base import SkillContext

    load_all_skills()
    sk = get_skill(skill_name)

    if not sk:
        click.echo(f"Error: Skill '{skill_name}' not found", err=True)
        click.echo("Run 'paperclaw skill list' to see available skills")
        sys.exit(1)

    # Parse config
    config_dict = {}
    for item in config:
        if "=" in item:
            key, value = item.split("=", 1)
            config_dict[key] = value

    # Create context
    context = SkillContext.from_project(
        project_dir,
        language=lang,
        verbose=verbose,
        config=config_dict,
    )

    click.echo(f"Running skill: {skill_name}")
    click.echo("-" * 40)

    result = sk.run(context)

    # Display results
    click.echo(f"\nStatus: {result.status.value}")
    click.echo(f"Duration: {result.metrics.get('duration_ms', 0):.0f}ms")

    if result.messages:
        click.echo("\nMessages:")
        for msg in result.messages:
            click.echo(f"  {msg}")

    if result.errors:
        click.echo("\nErrors:")
        for err in result.errors:
            click.echo(f"  {err}", err=True)

    if result.artifacts:
        click.echo("\nArtifacts:")
        for artifact in result.artifacts:
            click.echo(f"  {artifact}")

    if verbose and result.data:
        click.echo("\nData:")
        for key, value in result.data.items():
            if isinstance(value, (dict, list)):
                click.echo(f"  {key}: <{type(value).__name__}>")
            else:
                click.echo(f"  {key}: {value}")

    if output:
        Path(output).write_text(result.to_json(), encoding="utf-8")
        click.echo(f"\nResult saved to {output}")


@skill.command("pipeline")
@click.argument("pipeline_name", type=click.Choice(["build", "qa", "full"]))
@click.argument("project_dir")
@click.option("--lang", default="en", type=click.Choice(["en", "ja"]),
              help="Target language")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--output", "-o", default=None, help="Save result JSON to file")
def skill_pipeline(pipeline_name, project_dir, lang, verbose, output):
    """Run a predefined skill pipeline.

    Pipelines:
        build - Parse spec, generate LaTeX, compile PDF
        qa    - Parse spec, run all QA checks
        full  - Build + QA (complete workflow)

    Examples:
        paperclaw skill pipeline build ./my_paper/
        paperclaw skill pipeline qa ./my_paper/ -v
        paperclaw skill pipeline full ./my_paper/ --lang ja
    """
    from .skills.orchestrator import Orchestrator, PipelineStep
    from .skills.base import SkillContext

    orchestrator = Orchestrator()

    # Get pipeline steps
    if pipeline_name == "build":
        steps = orchestrator.build_pipeline()
    elif pipeline_name == "qa":
        steps = orchestrator.qa_pipeline()
    else:  # full
        steps = orchestrator.full_pipeline()

    # Create context
    context = SkillContext.from_project(
        project_dir,
        language=lang,
        verbose=verbose,
    )

    click.echo(f"Running pipeline: {pipeline_name}")
    click.echo(f"Steps: {', '.join(s.skill_name for s in steps)}")
    click.echo("-" * 60)

    result = orchestrator.run(steps, context, verbose=verbose)

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("Pipeline Summary")
    click.echo("=" * 60)
    click.echo(f"Status: {result.status.value}")
    click.echo(f"Total duration: {result.total_duration_ms:.0f}ms")
    click.echo(f"Steps completed: {result.steps_completed}")
    click.echo(f"Steps skipped: {result.steps_skipped}")
    click.echo(f"Steps failed: {result.steps_failed}")

    # Per-skill summary
    click.echo("\nPer-skill results:")
    for skill_name, skill_result in result.results.items():
        status_icon = "✓" if skill_result.success else "✗"
        duration = skill_result.metrics.get("duration_ms", 0)
        click.echo(f"  {status_icon} {skill_name}: {skill_result.status.value} ({duration:.0f}ms)")

    if output:
        Path(output).write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        click.echo(f"\nFull result saved to {output}")


if __name__ == "__main__":
    cli()
