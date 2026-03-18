"""QA Figures Skill - Check figure quality and extract text via OCR."""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import re

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@dataclass
class FigureCheckResult:
    """Result of figure quality check."""
    fig_id: str
    path: str
    exists: bool
    resolution_ok: bool
    width: int = 0
    height: int = 0
    dpi: int = 0
    ocr_text: str = ""
    labels_found: list[str] = None
    issues: list[str] = None

    def __post_init__(self):
        if self.labels_found is None:
            self.labels_found = []
        if self.issues is None:
            self.issues = []


@register_skill
class QaFiguresSkill(Skill):
    """Check figure quality and extract text via OCR.

    Input:
        - Paper specification with figures
        - Figure files

    Output:
        - Quality check results
        - OCR extracted text
        - Detected labels/numbers
    """

    MIN_DPI = 150
    MIN_DIMENSION = 300

    @property
    def name(self) -> str:
        return "qa-figures"

    @property
    def description(self) -> str:
        return "Check figure quality and extract text via OCR"

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)

        figures = context.spec.get("figures", {})
        if not figures:
            result.add_message("No figures to check")
            return result

        if isinstance(figures, list):
            # Convert list format to dict
            figures = {f.get("id", f"fig_{i}"): f for i, f in enumerate(figures)}

        check_results = []
        issues_count = 0

        for fig_id, fig_data in figures.items():
            fig_path = fig_data.get("path", "")
            full_path = context.project_dir / fig_path

            check_result = self._check_figure(fig_id, full_path)
            check_results.append(check_result)

            if check_result.issues:
                issues_count += len(check_result.issues)
                for issue in check_result.issues:
                    result.add_message(f"[{fig_id}] {issue}")

        result.data["figures"] = [vars(r) for r in check_results]
        result.metrics["figures_checked"] = len(check_results)
        result.metrics["issues_found"] = issues_count

        if issues_count > 0:
            result.status = SkillStatus.WARNING
            result.add_message(f"Checked {len(check_results)} figures, found {issues_count} issues")
        else:
            result.add_message(f"All {len(check_results)} figures passed quality checks")

        return result

    def _check_figure(self, fig_id: str, path: Path) -> FigureCheckResult:
        """Check a single figure."""
        check_result = FigureCheckResult(
            fig_id=fig_id,
            path=str(path),
            exists=path.exists(),
            resolution_ok=False,
        )

        if not path.exists():
            check_result.issues.append("File not found")
            return check_result

        # Check image properties
        try:
            from PIL import Image
            with Image.open(path) as img:
                check_result.width = img.width
                check_result.height = img.height

                # Calculate DPI (assume 72 if not set)
                dpi = img.info.get("dpi", (72, 72))
                check_result.dpi = int(dpi[0]) if isinstance(dpi, tuple) else int(dpi)

                # Check resolution
                if check_result.width >= self.MIN_DIMENSION and check_result.height >= self.MIN_DIMENSION:
                    check_result.resolution_ok = True
                else:
                    check_result.issues.append(
                        f"Low resolution: {check_result.width}x{check_result.height} "
                        f"(min {self.MIN_DIMENSION}x{self.MIN_DIMENSION})"
                    )

                if check_result.dpi < self.MIN_DPI:
                    check_result.issues.append(
                        f"Low DPI: {check_result.dpi} (min {self.MIN_DPI})"
                    )

        except ImportError:
            check_result.issues.append("PIL not available for image analysis")
        except Exception as e:
            check_result.issues.append(f"Image analysis error: {e}")

        # OCR extraction
        try:
            ocr_text = self._extract_text_ocr(path)
            check_result.ocr_text = ocr_text

            # Find labels
            labels = self._find_labels(ocr_text)
            check_result.labels_found = labels

            if not labels:
                check_result.issues.append("No axis labels detected")

        except Exception as e:
            check_result.issues.append(f"OCR error: {e}")

        return check_result

    def _extract_text_ocr(self, path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter

            with Image.open(path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Preprocessing for better OCR
                img = ImageEnhance.Contrast(img).enhance(1.5)
                img = img.filter(ImageFilter.SHARPEN)

                # Run OCR with English + Japanese
                text = pytesseract.image_to_string(img, lang="eng+jpn")
                return text.strip()

        except ImportError:
            return ""
        except Exception:
            return ""

    def _find_labels(self, text: str) -> list[str]:
        """Find axis labels and common terms in OCR text."""
        common_labels = [
            # English
            "epoch", "epochs", "loss", "accuracy", "acc",
            "precision", "recall", "f1", "score",
            "training", "validation", "test",
            "batch", "learning rate", "lr",
            "model", "time", "iteration",
            # Japanese
            "エポック", "損失", "精度", "学習", "検証",
            "モデル", "時間", "反復",
        ]

        found = []
        text_lower = text.lower()

        for label in common_labels:
            if label.lower() in text_lower:
                found.append(label)

        # Also look for numbers (potential data values)
        numbers = re.findall(r'\b\d+\.?\d*\b', text)
        if numbers:
            found.append(f"{len(numbers)} numbers detected")

        return found
