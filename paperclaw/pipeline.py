"""Main pipeline for PaperClaw - orchestrates the paper generation process."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from .models import PaperSpec, BilingualText, Section, Author


class Pipeline:
    """Main pipeline that coordinates data analysis, figure generation, and PDF building."""

    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.spec_path = self.project_dir / "paper_spec.yaml"
        self.figures_dir = self.project_dir / "figures"
        self.output_dir = self.project_dir / "output"
        self.data_dir = self.project_dir / "data"

    def init_project(self, title_en: str = "", title_ja: str = "",
                     template: str = "twocol",
                     authors: list[dict] | None = None) -> PaperSpec:
        """Initialize a new paper project with directory structure."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        spec = PaperSpec.create_template(
            title_en=title_en,
            title_ja=title_ja,
            template=template,
        )

        if authors:
            spec.authors = [Author(**a) for a in authors]

        spec.save(self.spec_path)
        return spec

    def load_spec(self) -> PaperSpec:
        """Load the current paper specification."""
        if not self.spec_path.exists():
            raise FileNotFoundError(f"No paper_spec.yaml found in {self.project_dir}")
        return PaperSpec.load(self.spec_path)

    def save_spec(self, spec: PaperSpec):
        """Save the paper specification."""
        spec.save(self.spec_path)

    def analyze_data(self, data_path: str | Path) -> dict[str, Any]:
        """Analyze input data and return structured summary.

        Supports CSV and JSON files. Returns a dict with:
        - format: file format detected
        - columns: list of column names (CSV)
        - rows: number of rows
        - summary: basic statistics
        - suggested_figures: figure types that might be useful
        """
        data_path = Path(data_path)
        if not data_path.exists():
            raise FileNotFoundError(f"Data file not found: {data_path}")

        suffix = data_path.suffix.lower()

        if suffix == ".csv":
            return self._analyze_csv(data_path)
        elif suffix == ".json":
            return self._analyze_json(data_path)
        elif suffix in (".yaml", ".yml"):
            return self._analyze_yaml(data_path)
        else:
            return {"format": suffix, "note": "Unsupported format for auto-analysis"}

    def _analyze_csv(self, path: Path) -> dict:
        import pandas as pd

        df = pd.read_csv(path)
        summary = {
            "format": "csv",
            "columns": list(df.columns),
            "rows": len(df),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "summary": {},
            "suggested_figures": [],
        }

        # Basic statistics for numeric columns
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            stats = df[numeric_cols].describe().to_dict()
            summary["summary"] = {col: {k: round(v, 4) for k, v in s.items()} for col, s in stats.items()}

        # Suggest figure types
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        if len(numeric_cols) >= 2:
            summary["suggested_figures"].append("scatter")
            summary["suggested_figures"].append("heatmap")
        if numeric_cols and cat_cols:
            summary["suggested_figures"].append("bar")
            summary["suggested_figures"].append("box")
            summary["suggested_figures"].append("violin")
        if len(numeric_cols) >= 1:
            summary["suggested_figures"].append("line")
        if cat_cols:
            summary["suggested_figures"].append("pie")

        return summary

    def _analyze_json(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        summary = {
            "format": "json",
            "type": type(data).__name__,
            "suggested_figures": [],
        }

        if isinstance(data, list):
            summary["rows"] = len(data)
            if data and isinstance(data[0], dict):
                summary["columns"] = list(data[0].keys())
        elif isinstance(data, dict):
            summary["keys"] = list(data.keys())

        return summary

    def _analyze_yaml(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return {
            "format": "yaml",
            "type": type(data).__name__,
            "keys": list(data.keys()) if isinstance(data, dict) else [],
        }

    def generate_figures(self, figure_specs: list[dict] | None = None) -> list[str]:
        """Generate figures from specifications."""
        from .figure_engine import FigureEngine

        engine = FigureEngine(
            palette_file=str(Path(__file__).parent / "assets" / "color_palettes.json")
        )

        spec = self.load_spec()
        if figure_specs is None:
            # Use figure specs from paper_spec
            figure_specs = []
            for fig_id, fig_data in spec.figures.items():
                if fig_data.path:
                    figure_specs.append({"output": str(self.project_dir / fig_data.path)})

        results = []
        for fs in figure_specs:
            # Ensure output path is within project
            if not Path(fs.get("output", "")).is_absolute():
                fs["output"] = str(self.figures_dir / fs.get("output", "figure.pdf"))
            results.append(engine.create_figure(fs))

        return results

    def build_pdf(self, language: str = "en") -> str:
        """Build PDF for specified language using XeLaTeX."""
        from .latex_builder import LaTeXBuilder

        spec = self.load_spec()
        builder = LaTeXBuilder()

        self.output_dir.mkdir(exist_ok=True)
        title = spec.meta.get("title", {})
        if isinstance(title, dict):
            safe_title = title.get(language, "paper")[:30]
        else:
            safe_title = str(title)[:30]

        # Clean filename
        safe_title = "".join(c for c in safe_title if c.isalnum() or c in "._- ")
        if not safe_title:
            safe_title = "paper"

        output_path = str(self.output_dir / f"{safe_title}_{language}.pdf")
        return builder.build(spec.to_dict(), output_path, language=language)

    def build_all(self) -> dict[str, str]:
        """Build PDFs for all languages."""
        results = {}
        for lang in ("en", "ja"):
            try:
                results[lang] = self.build_pdf(lang)
            except Exception as e:
                results[lang] = f"Error: {e}"
        return results

    def preview_html(self, language: str = "en") -> str:
        """Generate HTML preview of the paper."""
        from .pdf_builder import PDFBuilder

        spec = self.load_spec()
        builder = PDFBuilder()
        return builder.preview_html(spec.to_dict(), language=language)

    def auto_generate(
        self,
        overview: str,
        data_paths: list[str | Path] | None = None,
        language: str = "both",
        title_en: str = "Untitled Paper",
        title_ja: str = "無題の論文",
        template: str = "twocol",
        authors: list[dict] | None = None,
        build: bool = True,
    ) -> PaperSpec:
        """Auto-generate a complete paper from data and research overview.

        Uses Claude Code CLI to draft all sections, then builds PDF.

        Args:
            overview: Natural language research overview, or path to a .txt file.
            data_paths: Paths to data files (CSV/JSON/YAML) to analyze.
            language: "en", "ja", or "both".
            title_en: Paper title in English.
            title_ja: Paper title in Japanese.
            template: LaTeX template name.
            authors: List of author dicts.
            build: Whether to build PDF after generation.

        Returns:
            The generated PaperSpec.
        """
        from .text_generator import TextGenerator

        # Setup directories
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        # Read overview from file if it's a path (short strings only, to avoid OS errors)
        if len(overview) < 260 and not overview.count("\n"):
            try:
                overview_path = Path(overview)
                if overview_path.exists() and overview_path.is_file():
                    overview = overview_path.read_text(encoding="utf-8")
            except OSError:
                pass  # Not a valid path, treat as text

        # Analyze data files
        combined_analysis = self._collect_data_analyses(data_paths)

        # Generate paper text via Claude Code
        generator = TextGenerator()
        spec, extras = generator.generate_paper(
            overview=overview,
            data_analysis=combined_analysis,
            title_en=title_en,
            title_ja=title_ja,
            authors=authors,
            template=template,
        )

        # Render Mermaid diagrams to PNG
        diagrams = extras.get("diagrams", {})
        if diagrams:
            self._render_diagrams(diagrams)

        # Render data figures via FigureEngine (matplotlib/seaborn)
        data_figures = extras.get("data_figures", {})
        if data_figures:
            self._render_data_figures(data_figures)

        # Save generated spec
        spec.save(self.spec_path)

        # Build PDFs
        results = {}
        if build:
            if language in ("en", "both"):
                try:
                    results["en"] = self.build_pdf("en")
                except Exception as e:
                    results["en"] = f"Error: {e}"
            if language in ("ja", "both"):
                try:
                    results["ja"] = self.build_pdf("ja")
                except Exception as e:
                    results["ja"] = f"Error: {e}"

        return spec

    def forge(
        self,
        experiment_dir: str | Path,
        extra_docs: list[str | Path] | None = None,
        overview: str = "",
        language: str = "both",
        title_en: str = "",
        title_ja: str = "",
        template: str = "twocol",
        authors: list[dict] | None = None,
        build: bool = True,
    ) -> PaperSpec:
        """Fully automated paper generation from an experiment directory.

        Scans experiment_dir for data, images, text, code.
        Optionally reads extra documents (Word, PDF, MD) for context.
        Generates the full paper via Claude Code, builds PDF.

        Args:
            experiment_dir: Path to experiment results directory.
            extra_docs: Optional list of external document paths (.docx, .pdf, .md).
            overview: Research overview text (optional; auto-derived if empty).
            language: "en", "ja", or "both".
            title_en: Paper title in English (auto-derived if empty).
            title_ja: Paper title in Japanese (auto-derived if empty).
            template: LaTeX template name.
            authors: List of author dicts.
            build: Whether to build PDF after generation.

        Returns:
            The generated PaperSpec.
        """
        from .experiment_collector import ExperimentCollector
        from .doc_extractor import extract_text
        from .text_generator import TextGenerator

        experiment_dir = Path(experiment_dir).resolve()

        # Setup project directories
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        # ── 1. Collect experiment data ──────────────────────────
        collector = ExperimentCollector(experiment_dir)
        collected = collector.collect()

        # ── 2. Analyze data files ───────────────────────────────
        data_analyses: list[dict] = []
        for data_file in collected["data_files"]:
            try:
                analysis = self.analyze_data(data_file)
                analysis["source_file"] = str(data_file.relative_to(experiment_dir))
                data_analyses.append(analysis)
            except Exception:
                pass

        combined_analysis: dict[str, Any] = {}
        if data_analyses:
            all_suggested = []
            for a in data_analyses:
                all_suggested.extend(a.get("suggested_figures", []))
            combined_analysis = {
                "files": [
                    {"path": a.get("source_file", ""), "analysis": a}
                    for a in data_analyses
                ],
                "all_suggested_figures": list(set(all_suggested)),
            }

        # ── 3. Copy images into project figures dir ─────────────
        for img in collected["images"]:
            dest = self.figures_dir / img.name
            if not dest.exists():
                shutil.copy2(img, dest)

        # ── 4. Extract text from external docs ──────────────────
        doc_texts: dict[str, str] = {}

        # Documents found inside experiment dir (docx, pdf, pptx)
        for doc in collected["documents"]:
            ext = doc.suffix.lower()
            if ext in (".docx", ".pdf", ".pptx"):
                try:
                    text = extract_text(doc)
                    if text and not text.startswith("["):
                        rel = str(doc.relative_to(experiment_dir))
                        doc_texts[rel] = text
                except Exception:
                    pass

        # Extra docs from outside the experiment dir
        if extra_docs:
            for doc_path in extra_docs:
                p = Path(doc_path)
                if not p.is_absolute():
                    p = Path.cwd() / p
                if p.exists():
                    try:
                        text = extract_text(p)
                        if text and not text.startswith("["):
                            doc_texts[p.name] = text
                    except Exception:
                        pass

        # ── 5. Read overview (from file or use collected text) ──
        if overview:
            # Check if it's a file path
            if len(overview) < 260 and not overview.count("\n"):
                try:
                    ov_path = Path(overview)
                    if ov_path.exists() and ov_path.is_file():
                        overview = ov_path.read_text(encoding="utf-8")
                except OSError:
                    pass
        else:
            # Auto-derive overview from collected text
            parts = []
            for fname, text in collected["text_contents"].items():
                parts.append(f"[{fname}]\n{text[:3000]}")
            for fname, text in doc_texts.items():
                parts.append(f"[{fname}]\n{text[:3000]}")
            if parts:
                overview = (
                    "The following documents and notes describe the experiment. "
                    "Please infer the research objective, methods, and findings "
                    "from these materials:\n\n" + "\n\n---\n\n".join(parts)
                )
            else:
                overview = (
                    "Experiment directory contents are shown in the additional context. "
                    "Please infer the research from the data files and directory structure."
                )

        # ── 6. Build extra context string ───────────────────────
        extra_context_parts = [collector.summarise(collected)]

        if doc_texts:
            extra_context_parts.append("## Extracted External Documents")
            for fname, text in doc_texts.items():
                extra_context_parts.append(f"### {fname}\n{text[:5000]}")

        extra_context = "\n\n".join(extra_context_parts)

        # ── 7. Auto-derive titles if not given ──────────────────
        if not title_en:
            # Try to derive from directory name
            dir_name = experiment_dir.name.replace("_", " ").replace("-", " ")
            title_en = f"Study: {dir_name}"
        if not title_ja:
            title_ja = "実験研究"

        # ── 8. Generate paper via Claude Code ────────────────────
        generator = TextGenerator()
        spec, extras = generator.generate_paper(
            overview=overview,
            data_analysis=combined_analysis,
            title_en=title_en,
            title_ja=title_ja,
            authors=authors,
            template=template,
            extra_context=extra_context,
        )

        # ── 9. Render Mermaid diagrams ──────────────────────────
        diagrams = extras.get("diagrams", {})
        if diagrams:
            self._render_diagrams(diagrams)

        # ── 9b. Render data figures (matplotlib/seaborn) ────────
        data_figures = extras.get("data_figures", {})
        if data_figures:
            self._render_data_figures(data_figures)

        # ── 10. Save spec ───────────────────────────────────────
        spec.save(self.spec_path)

        # ── 11. Build PDFs ──────────────────────────────────────
        if build:
            if language in ("en", "both"):
                try:
                    self.build_pdf("en")
                except Exception:
                    pass
            if language in ("ja", "both"):
                try:
                    self.build_pdf("ja")
                except Exception:
                    pass

        return spec

    def _render_diagrams(self, diagrams: dict[str, Any]) -> list[str]:
        """Render Mermaid diagrams to PNG using mmdc (mermaid-cli).

        Args:
            diagrams: Dict mapping fig_id -> {"mermaid": str, "caption": {...}, ...}

        Returns:
            List of generated file paths.
        """
        import shutil
        import subprocess
        import tempfile

        mmdc = shutil.which("mmdc")
        if not mmdc:
            # Try npx fallback
            mmdc = "npx"

        self.figures_dir.mkdir(parents=True, exist_ok=True)
        rendered = []

        for fig_id, diag_data in diagrams.items():
            mermaid_code = diag_data.get("mermaid", "")
            if not mermaid_code:
                continue

            output_path = self.figures_dir / f"{fig_id}.png"

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".mmd", delete=False, encoding="utf-8"
            ) as f:
                f.write(mermaid_code)
                mmd_path = f.name

            try:
                # Create puppeteer config for headless environments
                puppeteer_cfg = Path(tempfile.gettempdir()) / "pf_puppeteer.json"
                if not puppeteer_cfg.exists():
                    puppeteer_cfg.write_text(
                        '{"args":["--no-sandbox","--disable-setuid-sandbox"]}',
                        encoding="utf-8",
                    )

                # Create mermaid config for publication-quality rendering
                mermaid_cfg = Path(tempfile.gettempdir()) / "pf_mermaid_cfg.json"
                if not mermaid_cfg.exists():
                    mermaid_cfg.write_text(json.dumps({
                        "theme": "neutral",
                        "themeVariables": {
                            "fontSize": "14px",
                            "fontFamily": "Arial, Helvetica, sans-serif",
                        },
                    }), encoding="utf-8")

                if mmdc == "npx":
                    cmd = ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", mmd_path,
                           "-o", str(output_path), "-b", "white", "-s", "4",
                           "-p", str(puppeteer_cfg),
                           "-c", str(mermaid_cfg)]
                else:
                    cmd = [mmdc, "-i", mmd_path, "-o", str(output_path),
                           "-b", "white", "-s", "4",
                           "-p", str(puppeteer_cfg),
                           "-c", str(mermaid_cfg)]

                subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if output_path.exists():
                    rendered.append(str(output_path))

                # Also save the .mmd source for draw.io MCP editing
                mmd_save = self.figures_dir / f"{fig_id}.mmd"
                mmd_save.write_text(mermaid_code, encoding="utf-8")

            except Exception:
                pass  # Diagram rendering is best-effort
            finally:
                Path(mmd_path).unlink(missing_ok=True)

        return rendered

    def _render_data_figures(self, data_figures: dict[str, Any]) -> list[str]:
        """Render data figures via FigureEngine (matplotlib/seaborn, 300 dpi).

        Args:
            data_figures: Dict mapping fig_id -> figure spec with type, data, etc.

        Returns:
            List of generated file paths.
        """
        from .figure_engine import FigureEngine

        self.figures_dir.mkdir(parents=True, exist_ok=True)
        engine = FigureEngine()
        rendered = []

        for fig_id, fig_spec in data_figures.items():
            fig_type = fig_spec.get("type")
            fig_data = fig_spec.get("data")
            if not fig_type or not fig_data:
                continue

            output_path = str(self.figures_dir / fig_id)

            try:
                spec = {
                    "type": fig_type,
                    "data": fig_data,
                    "output": output_path,
                    "title": fig_spec.get("title", ""),
                    "xlabel": fig_spec.get("xlabel", ""),
                    "ylabel": fig_spec.get("ylabel", ""),
                    "figsize": fig_spec.get("figsize", [6, 4]),
                    "style": fig_spec.get("style", {}),
                }
                saved = engine.create_figure(spec)
                rendered.append(saved)
            except Exception:
                pass  # Figure rendering is best-effort

        return rendered

    def _collect_data_analyses(
        self, data_paths: list[str | Path] | None
    ) -> dict[str, Any]:
        """Analyze multiple data files and combine results."""
        if not data_paths:
            return {}

        files = []
        all_suggested_figures: list[str] = []

        for dp in data_paths:
            path = Path(dp)
            if not path.is_absolute():
                path = self.project_dir / path
            if not path.exists():
                # Try in data dir
                alt = self.data_dir / path.name
                if alt.exists():
                    path = alt
                else:
                    raise FileNotFoundError(f"Data file not found: {dp}")

            analysis = self.analyze_data(path)
            files.append({
                "path": str(path.name),
                "analysis": analysis,
            })
            all_suggested_figures.extend(analysis.get("suggested_figures", []))

        return {
            "files": files,
            "all_suggested_figures": list(set(all_suggested_figures)),
        }
