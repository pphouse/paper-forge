"""PDF Compile Skill - Compile LaTeX to PDF."""

from __future__ import annotations

from pathlib import Path
import subprocess
import shutil
import tempfile

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@register_skill
class PdfCompileSkill(Skill):
    """Compile LaTeX source to PDF.

    Input:
        - LaTeX source file or content
        - Figure assets

    Output:
        - Compiled PDF file
    """

    @property
    def name(self) -> str:
        return "pdf-compile"

    @property
    def description(self) -> str:
        return "Compile LaTeX source to PDF using XeLaTeX"

    def get_dependencies(self) -> list[str]:
        return ["latex-gen"]

    def validate_input(self, context: SkillContext) -> list[str]:
        errors = super().validate_input(context)

        # Check for xelatex
        result = subprocess.run(["which", "xelatex"], capture_output=True)
        if result.returncode != 0:
            errors.append("XeLaTeX not found. Please install TeX distribution.")

        return errors

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)

        # Get LaTeX source
        latex_source = context.config.get("latex_source")
        latex_file = context.config.get("latex_file")

        if latex_file:
            latex_file = Path(latex_file)
            if latex_file.exists():
                latex_source = latex_file.read_text(encoding="utf-8")

        if not latex_source:
            # Try to find in output directory
            latex_dir = context.project_dir / "output" / "latex"
            tex_files = list(latex_dir.glob(f"paper_{context.language}.tex"))
            if tex_files:
                latex_file = tex_files[0]
                latex_source = latex_file.read_text(encoding="utf-8")
            else:
                result.status = SkillStatus.ERROR
                result.add_error("No LaTeX source provided or found")
                return result

        # Compile
        output_dir = context.project_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        title = context.spec.get("meta", {}).get("title", {})
        if isinstance(title, dict):
            title = title.get(context.language, title.get("en", "paper"))
        title_short = title[:40] if title else "paper"

        output_file = output_dir / f"{title_short}_{context.language}.pdf"

        try:
            pdf_path = self._compile_latex(
                latex_source,
                output_file,
                context.project_dir,
            )
            result.artifacts.append(Path(pdf_path))
            result.data["pdf_file"] = pdf_path
            result.add_message(f"Compiled PDF: {pdf_path}")
        except Exception as e:
            result.status = SkillStatus.ERROR
            result.add_error(f"PDF compilation failed: {e}")

        return result

    def _compile_latex(
        self,
        latex_source: str,
        output_path: Path,
        project_dir: Path,
    ) -> str:
        """Compile LaTeX to PDF."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Write source
            tex_file = tmpdir / "paper.tex"
            tex_file.write_text(latex_source, encoding="utf-8")

            # Copy figures
            figures_dir = project_dir / "figures"
            if figures_dir.exists():
                shutil.copytree(figures_dir, tmpdir / "figures")

            # Also check for figures in spec paths
            for line in latex_source.split('\n'):
                if 'includegraphics' in line:
                    # Extract path from \includegraphics{path}
                    import re
                    match = re.search(r'\\includegraphics[^{]*\{([^}]+)\}', line)
                    if match:
                        fig_path = match.group(1)
                        src = project_dir / fig_path
                        if src.exists():
                            dest = tmpdir / fig_path
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            if not dest.exists():
                                shutil.copy2(src, dest)

            # Run XeLaTeX twice for cross-references
            for i in range(2):
                proc = subprocess.run(
                    ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if proc.returncode != 0 and i == 1:
                    # Extract errors from log
                    log_text = proc.stdout or ""
                    errors = [l for l in log_text.split('\n') if l.startswith('!')]
                    error_msg = '\n'.join(errors[:5]) if errors else "XeLaTeX compilation failed"
                    raise RuntimeError(error_msg)

            # Copy output
            pdf_file = tmpdir / "paper.pdf"
            if not pdf_file.exists():
                raise RuntimeError("PDF was not generated")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_file, output_path)

            return str(output_path.resolve())
