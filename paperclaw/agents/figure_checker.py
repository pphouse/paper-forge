"""Figure Quality Checker for academic papers.

Checks for:
- Text overlap/readability issues
- Resolution and format quality
- Consistency between figures and text
- Axis labels and legends
- Japanese text support via OCR
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from PIL import Image, ImageEnhance, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


@dataclass
class FigureIssue:
    """An issue found in a figure."""
    severity: str  # "error", "warning", "info"
    category: str  # "overlap", "resolution", "labels", "consistency"
    message: str
    suggestion: str = ""


@dataclass
class FigureCheckResult:
    """Result of checking a single figure."""
    figure_id: str
    path: str
    exists: bool
    width: int = 0
    height: int = 0
    dpi_estimate: int = 0
    format: str = ""
    has_text: bool = False
    extracted_text: str = ""
    detected_labels: list[str] = field(default_factory=list)
    detected_numbers: list[str] = field(default_factory=list)
    issues: list[FigureIssue] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return self.exists and not any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass
class FigureCheckerReport:
    """Complete report from figure checker."""
    total_figures: int
    checked: int
    ok: int
    with_errors: int
    with_warnings: int
    results: list[FigureCheckResult]
    text_consistency_issues: list[dict] = field(default_factory=list)
    number_consistency_issues: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_figures": self.total_figures,
            "checked": self.checked,
            "ok": self.ok,
            "with_errors": self.with_errors,
            "with_warnings": self.with_warnings,
            "results": [
                {
                    "figure_id": r.figure_id,
                    "path": r.path,
                    "exists": r.exists,
                    "dimensions": f"{r.width}x{r.height}" if r.exists else "N/A",
                    "dpi": r.dpi_estimate,
                    "is_ok": r.is_ok,
                    "detected_labels": r.detected_labels,
                    "detected_numbers": r.detected_numbers,
                    "issues": [
                        {"severity": i.severity, "category": i.category, "message": i.message}
                        for i in r.issues
                    ],
                }
                for r in self.results
            ],
            "text_consistency_issues": self.text_consistency_issues,
            "number_consistency_issues": self.number_consistency_issues,
        }


class FigureChecker:
    """Checks figure quality and consistency in papers.

    Features:
    - Multi-language OCR support (English + Japanese)
    - Image preprocessing for better OCR accuracy
    - Number extraction and consistency checking
    - Label detection (axis labels, legends)
    - Resolution and format validation

    Usage:
        checker = FigureChecker(language="ja+en")
        report = checker.check_figures(paper_spec, project_dir)
        for result in report.results:
            if not result.is_ok:
                print(f"Issues in {result.figure_id}:")
                for issue in result.issues:
                    print(f"  [{issue.severity}] {issue.message}")
    """

    # Minimum recommended dimensions for print quality
    MIN_WIDTH = 600  # pixels
    MIN_HEIGHT = 400
    MIN_DPI = 150
    RECOMMENDED_DPI = 300

    # Common axis labels to detect
    COMMON_LABELS_EN = ["accuracy", "loss", "epoch", "precision", "recall", "f1", "time", "iteration"]
    COMMON_LABELS_JA = ["精度", "損失", "エポック", "適合率", "再現率", "時間", "反復"]

    def __init__(
        self,
        use_ocr: bool = True,
        language: str = "eng+jpn",
        preprocess: bool = True,
    ):
        """Initialize figure checker.

        Args:
            use_ocr: Whether to use OCR for text extraction
            language: Tesseract language code (e.g., "eng", "jpn", "eng+jpn")
            preprocess: Whether to preprocess images for better OCR
        """
        self.use_ocr = use_ocr and HAS_TESSERACT
        self.language = language
        self.preprocess = preprocess

        if use_ocr and not HAS_TESSERACT:
            logger.warning("pytesseract not available, OCR disabled")

        # Check if Japanese language pack is available
        if use_ocr and HAS_TESSERACT and "jpn" in language:
            try:
                langs = pytesseract.get_languages()
                if "jpn" not in langs:
                    logger.warning("Japanese OCR pack not found, falling back to English only")
                    self.language = "eng"
            except Exception:
                pass

    def _preprocess_for_ocr(self, img: "Image.Image") -> "Image.Image":
        """Preprocess image to improve OCR accuracy."""
        if not self.preprocess:
            return img

        try:
            # Convert to grayscale
            if img.mode != "L":
                img = img.convert("L")

            # Increase contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)

            # Sharpen
            img = img.filter(ImageFilter.SHARPEN)

            # Resize if too small (OCR works better on larger images)
            width, height = img.size
            if width < 1000:
                scale = 1000 / width
                img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)

            # Binarize (threshold)
            threshold = 128
            img = img.point(lambda p: 255 if p > threshold else 0)

            return img
        except Exception as e:
            logger.debug(f"Preprocessing failed: {e}")
            return img

    def _check_image_quality(self, img: "Image.Image", path: Path) -> list[FigureIssue]:
        """Check basic image quality."""
        issues = []

        width, height = img.size

        # Check resolution
        if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
            issues.append(FigureIssue(
                severity="warning",
                category="resolution",
                message=f"解像度が低い: {width}x{height} (推奨: {self.MIN_WIDTH}x{self.MIN_HEIGHT}以上)",
                suggestion="印刷品質のために高解像度画像の使用を検討してください",
            ))

        # Check aspect ratio
        aspect = width / height if height > 0 else 1
        if aspect > 4 or aspect < 0.25:
            issues.append(FigureIssue(
                severity="warning",
                category="layout",
                message=f"極端なアスペクト比: {aspect:.2f}",
                suggestion="非常に横長または縦長の図はレイアウトに収まらない可能性があります",
            ))

        # Check if image is mostly empty (white)
        if img.mode in ("RGB", "RGBA"):
            arr = np.array(img)
            if arr.shape[-1] >= 3:
                gray = np.mean(arr[..., :3], axis=-1)
                white_ratio = np.sum(gray > 250) / gray.size
                if white_ratio > 0.9:
                    issues.append(FigureIssue(
                        severity="info",
                        category="content",
                        message="画像の90%以上が白/空白です",
                        suggestion="図に意味のある内容が含まれているか確認してください",
                    ))

        # Check file format
        fmt = img.format or path.suffix.upper().replace(".", "")
        if fmt.lower() not in ("png", "pdf", "eps", "svg"):
            issues.append(FigureIssue(
                severity="info",
                category="format",
                message=f"フォーマット '{fmt}' は印刷に最適ではない可能性があります",
                suggestion="ラスター画像にはPNG、ベクター画像にはPDF/EPSの使用を検討してください",
            ))

        return issues

    def _check_text_overlap(self, img: "Image.Image") -> list[FigureIssue]:
        """Check for potential text overlap issues using image analysis."""
        issues = []

        try:
            from scipy import ndimage
        except ImportError:
            return issues

        try:
            arr = np.array(img.convert("RGB"))
            gray = np.mean(arr, axis=-1)

            # Calculate variance in sliding window
            window_size = 20
            local_mean = ndimage.uniform_filter(gray, window_size)
            local_sq_mean = ndimage.uniform_filter(gray**2, window_size)
            local_var = local_sq_mean - local_mean**2

            # High variance regions might be text
            text_mask = local_var > 500

            # Check for text near edges (might be cut off)
            height, width = text_mask.shape
            edge_margin = int(min(width, height) * 0.05)

            edge_text = (
                np.sum(text_mask[:edge_margin, :]) +
                np.sum(text_mask[-edge_margin:, :]) +
                np.sum(text_mask[:, :edge_margin]) +
                np.sum(text_mask[:, -edge_margin:])
            )

            if edge_text > 100:
                issues.append(FigureIssue(
                    severity="warning",
                    category="overlap",
                    message="画像端にテキストが存在する可能性があります（切れる恐れ）",
                    suggestion="ラベルや凡例に十分な余白を確保してください",
                ))

            # Check for dense text regions that might overlap
            labeled, num_features = ndimage.label(text_mask)
            if num_features > 50:
                issues.append(FigureIssue(
                    severity="info",
                    category="overlap",
                    message=f"多くのテキスト/詳細領域を検出 ({num_features})",
                    suggestion="テキスト要素が重なっていないか確認してください",
                ))

            # Check for overlapping bounding boxes
            if num_features > 1:
                objects = ndimage.find_objects(labeled)
                boxes = []
                for obj in objects:
                    if obj is not None:
                        y_slice, x_slice = obj
                        boxes.append((x_slice.start, y_slice.start, x_slice.stop, y_slice.stop))

                # Check for overlaps
                overlap_count = 0
                for i, box1 in enumerate(boxes):
                    for box2 in boxes[i+1:]:
                        if self._boxes_overlap(box1, box2):
                            overlap_count += 1

                if overlap_count > 5:
                    issues.append(FigureIssue(
                        severity="warning",
                        category="overlap",
                        message=f"テキスト領域の重複を{overlap_count}箇所検出",
                        suggestion="ラベル配置を見直してください",
                    ))

        except Exception as e:
            logger.debug(f"Text overlap check failed: {e}")

        return issues

    def _boxes_overlap(self, box1: tuple, box2: tuple) -> bool:
        """Check if two bounding boxes overlap."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2

        return not (x1_max < x2_min or x2_max < x1_min or
                   y1_max < y2_min or y2_max < y1_min)

    def _extract_text_ocr(self, img: "Image.Image") -> tuple[str, list[str], list[str]]:
        """Extract text from image using OCR.

        Returns:
            Tuple of (full_text, detected_labels, detected_numbers)
        """
        if not self.use_ocr:
            return "", [], []

        try:
            # Preprocess for better OCR
            processed = self._preprocess_for_ocr(img.copy())

            # Configure tesseract
            config = "--psm 6"  # Assume a single uniform block of text

            # Extract text
            text = pytesseract.image_to_string(processed, lang=self.language, config=config)
            text = text.strip()

            # Also try with original image for comparison
            text_original = pytesseract.image_to_string(img, lang=self.language, config=config)

            # Use longer result (usually more accurate)
            if len(text_original) > len(text):
                text = text_original

            # Extract labels
            detected_labels = []
            text_lower = text.lower()
            for label in self.COMMON_LABELS_EN + self.COMMON_LABELS_JA:
                if label.lower() in text_lower:
                    detected_labels.append(label)

            # Extract numbers (including decimals and percentages)
            detected_numbers = []
            # Percentages
            detected_numbers.extend(re.findall(r'\b(\d+\.?\d*)\s*%', text))
            # Decimals
            detected_numbers.extend(re.findall(r'\b(0\.\d+)\b', text))
            # Scientific notation
            detected_numbers.extend(re.findall(r'\b(\d+\.?\d*[eE][+-]?\d+)\b', text))
            # Regular numbers (exclude very common ones like 0, 1, 2)
            for num in re.findall(r'\b(\d+\.?\d*)\b', text):
                if float(num) > 2 or '.' in num:
                    detected_numbers.append(num)

            # Remove duplicates while preserving order
            detected_numbers = list(dict.fromkeys(detected_numbers))

            return text, detected_labels, detected_numbers

        except Exception as e:
            logger.debug(f"OCR failed: {e}")
            return "", [], []

    def _check_axis_labels(self, result: FigureCheckResult) -> list[FigureIssue]:
        """Check for presence of axis labels."""
        issues = []

        if not result.extracted_text:
            return issues

        # Check if common axis labels are present
        has_x_label = False
        has_y_label = False
        has_legend = False

        text_lower = result.extracted_text.lower()

        # Check for axis-related keywords
        x_keywords = ["epoch", "time", "iteration", "step", "batch", "エポック", "時間", "反復"]
        y_keywords = ["accuracy", "loss", "precision", "recall", "score", "精度", "損失", "スコア"]
        legend_keywords = ["train", "test", "val", "baseline", "proposed", "訓練", "テスト", "提案"]

        for kw in x_keywords:
            if kw in text_lower:
                has_x_label = True
                break

        for kw in y_keywords:
            if kw in text_lower:
                has_y_label = True
                break

        for kw in legend_keywords:
            if kw in text_lower:
                has_legend = True
                break

        # Only warn if this looks like a chart but is missing labels
        if result.detected_numbers and len(result.detected_numbers) > 5:
            if not has_x_label and not has_y_label:
                issues.append(FigureIssue(
                    severity="info",
                    category="labels",
                    message="軸ラベルが検出されませんでした",
                    suggestion="グラフには分かりやすい軸ラベルを付けてください",
                ))

        return issues

    def _check_figure(self, fig_id: str, fig_spec: dict, project_dir: Path) -> FigureCheckResult:
        """Check a single figure."""
        path_str = fig_spec.get("path", "")
        fig_path = project_dir / path_str

        result = FigureCheckResult(
            figure_id=fig_id,
            path=str(fig_path),
            exists=fig_path.exists(),
        )

        if not fig_path.exists():
            result.issues.append(FigureIssue(
                severity="error",
                category="missing",
                message=f"図ファイルが見つかりません: {path_str}",
                suggestion="指定されたパスにファイルが存在することを確認してください",
            ))
            return result

        if not HAS_PIL:
            result.issues.append(FigureIssue(
                severity="warning",
                category="dependency",
                message="PILが利用できないため、画像分析をスキップします",
            ))
            return result

        try:
            img = Image.open(fig_path)
            result.width, result.height = img.size
            result.format = img.format or fig_path.suffix.upper().replace(".", "")

            # Estimate DPI
            dpi = img.info.get("dpi", (72, 72))
            if isinstance(dpi, tuple):
                result.dpi_estimate = int(dpi[0])
            else:
                result.dpi_estimate = int(dpi)

            # Quality checks
            result.issues.extend(self._check_image_quality(img, fig_path))

            # Text overlap check
            result.issues.extend(self._check_text_overlap(img))

            # OCR for text extraction
            if self.use_ocr:
                text, labels, numbers = self._extract_text_ocr(img)
                result.extracted_text = text
                result.has_text = bool(text.strip())
                result.detected_labels = labels
                result.detected_numbers = numbers

                # Check for axis labels
                result.issues.extend(self._check_axis_labels(result))

        except Exception as e:
            result.issues.append(FigureIssue(
                severity="error",
                category="read_error",
                message=f"画像の読み込みに失敗: {e}",
            ))

        return result

    def _check_text_consistency(
        self,
        paper_spec: dict,
        figure_results: list[FigureCheckResult],
    ) -> list[dict]:
        """Check consistency between figure content and paper text."""
        issues = []

        # Extract text from paper
        paper_text = ""
        for section in paper_spec.get("sections", []):
            content = section.get("content", {})
            if isinstance(content, dict):
                paper_text += content.get("en", "") + " " + content.get("ja", "") + " "
            else:
                paper_text += str(content) + " "

        paper_text_lower = paper_text.lower()

        # Check if figure labels are mentioned in text
        for result in figure_results:
            for label in result.detected_labels:
                if label.lower() not in paper_text_lower:
                    issues.append({
                        "figure_id": result.figure_id,
                        "type": "unmentioned_label",
                        "message": f"図のラベル '{label}' が本文に記載されていません",
                        "severity": "info",
                    })

        return issues

    def _check_number_consistency(
        self,
        paper_spec: dict,
        figure_results: list[FigureCheckResult],
    ) -> list[dict]:
        """Check if numbers in figures match numbers in text."""
        issues = []

        # Extract numbers from paper text
        paper_numbers = set()
        for section in paper_spec.get("sections", []):
            content = section.get("content", {})
            if isinstance(content, dict):
                text = content.get("en", "") + " " + content.get("ja", "")
            else:
                text = str(content)

            # Percentages
            paper_numbers.update(re.findall(r'\b(\d+\.?\d*)\s*%', text))
            # Decimals
            paper_numbers.update(re.findall(r'\b0\.\d+\b', text))
            # Scientific notation
            paper_numbers.update(re.findall(r'\b\d+\.?\d*[eE][+-]?\d+\b', text))

        # Check figure numbers against paper numbers
        for result in figure_results:
            if result.detected_numbers:
                # Find significant numbers not in paper
                unmentioned = []
                for num in result.detected_numbers:
                    # Skip common axis values
                    try:
                        val = float(num.replace('%', ''))
                        if val in [0, 1, 10, 100, 0.5]:
                            continue
                    except ValueError:
                        pass

                    if num not in paper_numbers:
                        unmentioned.append(num)

                if unmentioned and len(unmentioned) <= 5:
                    issues.append({
                        "figure_id": result.figure_id,
                        "type": "unmentioned_values",
                        "values": unmentioned,
                        "message": f"図中の値が本文に記載されていません: {unmentioned}",
                        "severity": "info",
                    })

        return issues

    def check_figures(
        self,
        paper_spec: dict,
        project_dir: str | Path,
    ) -> FigureCheckerReport:
        """Check all figures in a paper specification.

        Args:
            paper_spec: Paper specification dict with "figures" key
            project_dir: Path to project directory containing figures

        Returns:
            FigureCheckerReport with check results
        """
        project_dir = Path(project_dir)
        figures = paper_spec.get("figures", {})

        results = []
        ok_count = 0
        error_count = 0
        warning_count = 0

        for fig_id, fig_spec in figures.items():
            if isinstance(fig_spec, str):
                fig_spec = {"path": fig_spec}

            result = self._check_figure(fig_id, fig_spec, project_dir)
            results.append(result)

            if result.is_ok:
                ok_count += 1
            if result.error_count > 0:
                error_count += 1
            if result.warning_count > 0:
                warning_count += 1

            logger.info(f"[{'OK' if result.is_ok else 'ISSUES'}] {fig_id}: {len(result.issues)} issues")

        # Check consistency
        text_consistency_issues = self._check_text_consistency(paper_spec, results)
        number_consistency_issues = self._check_number_consistency(paper_spec, results)

        return FigureCheckerReport(
            total_figures=len(figures),
            checked=len(results),
            ok=ok_count,
            with_errors=error_count,
            with_warnings=warning_count,
            results=results,
            text_consistency_issues=text_consistency_issues,
            number_consistency_issues=number_consistency_issues,
        )

    def suggest_improvements(self, report: FigureCheckerReport) -> list[str]:
        """Generate improvement suggestions based on report."""
        suggestions = []

        for result in report.results:
            if not result.exists:
                suggestions.append(f"図 '{result.figure_id}' のパスを作成または修正してください")
                continue

            for issue in result.issues:
                if issue.suggestion:
                    suggestions.append(f"[{result.figure_id}] {issue.suggestion}")

        # General suggestions
        if report.with_errors > 0:
            suggestions.insert(0, f"提出前に{report.with_errors}件の重大な図の問題を修正してください")

        if any(r.dpi_estimate < self.MIN_DPI for r in report.results if r.dpi_estimate > 0):
            suggestions.append("印刷品質のために画像解像度を300 DPIに上げることを検討してください")

        # Consistency suggestions
        if report.text_consistency_issues:
            suggestions.append("図と本文の用語の一貫性を確認してください")

        if report.number_consistency_issues:
            suggestions.append("図中の数値が本文で適切に説明されているか確認してください")

        return suggestions
