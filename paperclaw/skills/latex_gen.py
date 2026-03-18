"""LaTeX Generation Skill - Generate LaTeX from specification."""

from __future__ import annotations

from pathlib import Path

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@register_skill
class LatexGenSkill(Skill):
    """Generate LaTeX source from paper specification.

    Input:
        - Parsed paper specification
        - Target language (en, ja)

    Output:
        - LaTeX source file
        - Required assets (figures, bibliography)
    """

    @property
    def name(self) -> str:
        return "latex-gen"

    @property
    def description(self) -> str:
        return "Generate LaTeX source from paper specification"

    def get_dependencies(self) -> list[str]:
        return ["spec-parser"]

    def validate_input(self, context: SkillContext) -> list[str]:
        errors = super().validate_input(context)
        if not context.spec:
            errors.append("No specification provided")
        return errors

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)

        # Import the latex builder
        try:
            from ..latex_builder import LaTeXBuilder
        except ImportError as e:
            result.status = SkillStatus.ERROR
            result.add_error(f"LaTeX builder module not available: {e}")
            return result

        builder = LaTeXBuilder()
        language = context.language

        # Generate LaTeX
        try:
            latex_source = builder._build_latex(context.spec, language)
        except Exception as e:
            result.status = SkillStatus.ERROR
            result.add_error(f"LaTeX generation failed: {e}")
            return result

        # Write to output
        output_dir = context.project_dir / "output" / "latex"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"paper_{language}.tex"

        output_file.write_text(latex_source, encoding="utf-8")
        result.artifacts.append(output_file)

        # Copy figures
        figures_copied = self._copy_figures(context, output_dir)
        result.data["figures_copied"] = figures_copied

        result.data["latex_file"] = str(output_file)
        result.data["latex_source"] = latex_source
        result.metrics["latex_lines"] = len(latex_source.split('\n'))
        result.metrics["figures_copied"] = len(figures_copied)
        result.add_message(f"Generated LaTeX: {output_file}")

        return result

    def _copy_figures(self, context: SkillContext, output_dir: Path) -> list[str]:
        """Copy figures to output directory."""
        import shutil

        copied = []
        figures = context.spec.get("figures", {})

        if isinstance(figures, dict):
            for fig_id, fig_data in figures.items():
                fig_path = fig_data.get("path", "")
                if fig_path:
                    src = context.project_dir / fig_path
                    if src.exists():
                        dest = output_dir / fig_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)
                        copied.append(fig_path)

        return copied
