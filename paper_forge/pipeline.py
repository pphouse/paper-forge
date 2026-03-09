"""Main pipeline for PaperForge - orchestrates the paper generation process."""

from __future__ import annotations

import csv
import json
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
        """Build PDF for specified language."""
        from .pdf_builder import PDFBuilder

        spec = self.load_spec()
        builder = PDFBuilder()

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
