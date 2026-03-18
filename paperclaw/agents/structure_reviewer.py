"""Structure Reviewer for academic papers.

Analyzes:
- Section flow and logical consistency
- Missing or redundant sections
- Balance between sections
- Cross-references and citations
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Standard academic paper sections
STANDARD_SECTIONS = {
    "abstract": ["abstract", "概要", "要旨"],
    "introduction": ["introduction", "はじめに", "序論", "背景"],
    "methods": ["methods", "methodology", "materials and methods", "手法", "方法", "材料と方法"],
    "results": ["results", "結果", "実験結果"],
    "discussion": ["discussion", "考察", "議論"],
    "conclusion": ["conclusion", "conclusions", "結論", "まとめ"],
    "references": ["references", "bibliography", "参考文献", "文献"],
    "acknowledgments": ["acknowledgments", "acknowledgements", "謝辞"],
}

# Expected section order
EXPECTED_ORDER = ["introduction", "methods", "results", "discussion", "conclusion"]

# Transition phrases that indicate good flow
TRANSITION_PHRASES = {
    "contrast": ["however", "on the other hand", "in contrast", "nevertheless", "一方", "しかし"],
    "addition": ["furthermore", "moreover", "additionally", "in addition", "さらに", "また"],
    "cause_effect": ["therefore", "thus", "consequently", "as a result", "したがって", "その結果"],
    "example": ["for example", "for instance", "specifically", "例えば", "具体的には"],
    "conclusion": ["in conclusion", "to summarize", "in summary", "結論として", "まとめると"],
}


@dataclass
class StructureIssue:
    """An issue found in paper structure."""
    severity: str  # "error", "warning", "info"
    category: str  # "missing", "order", "balance", "flow", "reference"
    message: str
    section: str = ""
    suggestion: str = ""


@dataclass
class SectionAnalysis:
    """Analysis of a single section."""
    name: str
    word_count: int
    paragraph_count: int
    has_figures: bool
    has_tables: bool
    figure_refs: list[str]
    table_refs: list[str]
    citation_count: int
    transition_score: float  # 0-1, higher = better transitions
    detected_type: str = ""  # Matched standard section type


@dataclass
class StructureReport:
    """Complete structure analysis report."""
    total_sections: int
    total_word_count: int
    detected_sections: dict[str, bool]  # Standard section -> present
    section_order_correct: bool
    sections: list[SectionAnalysis]
    issues: list[StructureIssue]
    overall_score: float  # 0-100

    def to_dict(self) -> dict:
        return {
            "total_sections": self.total_sections,
            "total_word_count": self.total_word_count,
            "detected_sections": self.detected_sections,
            "section_order_correct": self.section_order_correct,
            "overall_score": self.overall_score,
            "sections": [
                {
                    "name": s.name,
                    "type": s.detected_type,
                    "word_count": s.word_count,
                    "has_figures": s.has_figures,
                    "has_tables": s.has_tables,
                    "transition_score": s.transition_score,
                }
                for s in self.sections
            ],
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
        }


class StructureReviewer:
    """Reviews paper structure and logical flow.

    Usage:
        reviewer = StructureReviewer()
        report = reviewer.analyze(paper_spec)
        print(f"Structure score: {report.overall_score}/100")
        for issue in report.issues:
            print(f"[{issue.severity}] {issue.message}")
    """

    def __init__(self, language: str = "en"):
        """Initialize structure reviewer.

        Args:
            language: Primary language for analysis ("en" or "ja")
        """
        self.language = language

    def _get_text(self, obj: Any) -> str:
        """Extract text from bilingual object."""
        if isinstance(obj, dict):
            return obj.get(self.language, obj.get("en", ""))
        return str(obj) if obj else ""

    def _detect_section_type(self, heading: str) -> str:
        """Detect standard section type from heading."""
        heading_lower = heading.lower().strip()

        for section_type, keywords in STANDARD_SECTIONS.items():
            for keyword in keywords:
                if keyword.lower() in heading_lower:
                    return section_type

        return "other"

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        # Handle both English and Japanese
        # For Japanese, count characters as rough word estimate
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        japanese_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', text))
        return english_words + japanese_chars // 2  # Rough estimate

    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs in text."""
        if not text:
            return 0
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        return len(paragraphs)

    def _calculate_transition_score(self, text: str) -> float:
        """Calculate how well the text uses transitions."""
        if not text:
            return 0.5

        text_lower = text.lower()
        transition_count = 0
        categories_used = set()

        for category, phrases in TRANSITION_PHRASES.items():
            for phrase in phrases:
                if phrase.lower() in text_lower:
                    transition_count += 1
                    categories_used.add(category)

        # Score based on variety and frequency
        word_count = self._count_words(text)
        if word_count < 100:
            return 0.5  # Too short to judge

        frequency_score = min(transition_count / (word_count / 200), 1.0)
        variety_score = len(categories_used) / len(TRANSITION_PHRASES)

        return (frequency_score + variety_score) / 2

    def _find_figure_refs(self, text: str) -> list[str]:
        """Find figure references in text."""
        patterns = [
            r'[Ff]igure\s*(\d+)',
            r'[Ff]ig\.\s*(\d+)',
            r'図\s*(\d+)',
        ]
        refs = []
        for pattern in patterns:
            refs.extend(re.findall(pattern, text))
        return refs

    def _find_table_refs(self, text: str) -> list[str]:
        """Find table references in text."""
        patterns = [
            r'[Tt]able\s*(\d+)',
            r'表\s*(\d+)',
        ]
        refs = []
        for pattern in patterns:
            refs.extend(re.findall(pattern, text))
        return refs

    def _count_citations(self, text: str) -> int:
        """Count citation references in text."""
        patterns = [
            r'\[[\d,\s-]+\]',  # [1], [1,2], [1-3]
            r'\([A-Z][a-z]+\s*(?:et al\.)?,?\s*\d{4}\)',  # (Author, 2024)
            r'\\cite\{[^}]+\}',  # LaTeX citations
        ]
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text))
        return count

    def _analyze_section(self, section: dict, figures: dict, tables: dict) -> SectionAnalysis:
        """Analyze a single section."""
        heading = self._get_text(section.get("heading", ""))
        content = self._get_text(section.get("content", ""))

        # Include subsections
        for subsec in section.get("subsections", []):
            sub_content = self._get_text(subsec.get("content", ""))
            content += "\n\n" + sub_content

        figure_ids = section.get("figures", [])
        table_ids = section.get("tables", [])

        return SectionAnalysis(
            name=heading,
            word_count=self._count_words(content),
            paragraph_count=self._count_paragraphs(content),
            has_figures=bool(figure_ids),
            has_tables=bool(table_ids),
            figure_refs=self._find_figure_refs(content),
            table_refs=self._find_table_refs(content),
            citation_count=self._count_citations(content),
            transition_score=self._calculate_transition_score(content),
            detected_type=self._detect_section_type(heading),
        )

    def _check_section_order(self, sections: list[SectionAnalysis]) -> tuple[bool, list[StructureIssue]]:
        """Check if sections are in expected order."""
        issues = []

        # Get detected types in order
        detected_order = [s.detected_type for s in sections if s.detected_type in EXPECTED_ORDER]

        # Check order
        expected_idx = 0
        for section_type in detected_order:
            while expected_idx < len(EXPECTED_ORDER) and EXPECTED_ORDER[expected_idx] != section_type:
                expected_idx += 1
            if expected_idx >= len(EXPECTED_ORDER):
                issues.append(StructureIssue(
                    severity="warning",
                    category="order",
                    message=f"Section '{section_type}' appears out of expected order",
                    suggestion="Standard order: Introduction → Methods → Results → Discussion → Conclusion",
                ))
                return False, issues
            expected_idx += 1

        return True, issues

    def _check_missing_sections(self, detected: dict[str, bool]) -> list[StructureIssue]:
        """Check for missing standard sections."""
        issues = []
        required = ["introduction", "methods", "results", "conclusion"]

        for section in required:
            if not detected.get(section):
                issues.append(StructureIssue(
                    severity="warning",
                    category="missing",
                    message=f"Standard section '{section}' not detected",
                    suggestion=f"Consider adding a {section.title()} section",
                ))

        return issues

    def _check_balance(self, sections: list[SectionAnalysis]) -> list[StructureIssue]:
        """Check section length balance."""
        issues = []

        if not sections:
            return issues

        word_counts = {s.detected_type: s.word_count for s in sections if s.detected_type != "other"}

        # Check for very short sections
        for section_type, count in word_counts.items():
            if count < 100 and section_type in EXPECTED_ORDER:
                issues.append(StructureIssue(
                    severity="warning",
                    category="balance",
                    section=section_type,
                    message=f"Section '{section_type}' is very short ({count} words)",
                    suggestion="Consider expanding this section with more detail",
                ))

        # Check for imbalance between Results and Discussion
        results_count = word_counts.get("results", 0)
        discussion_count = word_counts.get("discussion", 0)

        if results_count > 0 and discussion_count > 0:
            ratio = discussion_count / results_count
            if ratio < 0.3:
                issues.append(StructureIssue(
                    severity="info",
                    category="balance",
                    message="Discussion section is much shorter than Results",
                    suggestion="Consider expanding interpretation and implications in Discussion",
                ))

        return issues

    def _check_references(self, sections: list[SectionAnalysis], figures: dict, tables: dict) -> list[StructureIssue]:
        """Check figure/table references."""
        issues = []

        # Collect all referenced figures and tables
        all_fig_refs = set()
        all_tab_refs = set()

        for section in sections:
            all_fig_refs.update(section.figure_refs)
            all_tab_refs.update(section.table_refs)

        # Check for unreferenced figures
        fig_ids = set(str(i+1) for i in range(len(figures)))
        unreferenced_figs = fig_ids - all_fig_refs

        if unreferenced_figs and figures:
            issues.append(StructureIssue(
                severity="warning",
                category="reference",
                message=f"Some figures may not be referenced in text: {unreferenced_figs}",
                suggestion="Ensure all figures are referenced and discussed in the text",
            ))

        # Check for unreferenced tables
        tab_ids = set(str(i+1) for i in range(len(tables)))
        unreferenced_tabs = tab_ids - all_tab_refs

        if unreferenced_tabs and tables:
            issues.append(StructureIssue(
                severity="warning",
                category="reference",
                message=f"Some tables may not be referenced in text: {unreferenced_tabs}",
                suggestion="Ensure all tables are referenced and discussed in the text",
            ))

        # Check citation density
        total_words = sum(s.word_count for s in sections)
        total_citations = sum(s.citation_count for s in sections)

        if total_words > 1000 and total_citations < 5:
            issues.append(StructureIssue(
                severity="info",
                category="reference",
                message=f"Low citation density ({total_citations} citations in {total_words} words)",
                suggestion="Consider adding more citations to support claims",
            ))

        return issues

    def _calculate_score(self, report_data: dict) -> float:
        """Calculate overall structure score."""
        score = 100.0

        # Deduct for missing sections
        for section in ["introduction", "methods", "results", "conclusion"]:
            if not report_data["detected"].get(section):
                score -= 10

        # Deduct for order issues
        if not report_data["order_correct"]:
            score -= 10

        # Deduct for issues
        for issue in report_data["issues"]:
            if issue.severity == "error":
                score -= 15
            elif issue.severity == "warning":
                score -= 5
            elif issue.severity == "info":
                score -= 1

        return max(0, min(100, score))

    def analyze(self, paper_spec: dict) -> StructureReport:
        """Analyze paper structure.

        Args:
            paper_spec: Paper specification dict

        Returns:
            StructureReport with analysis results
        """
        sections_data = paper_spec.get("sections", [])
        figures = paper_spec.get("figures", {})
        tables = paper_spec.get("tables", {})

        # Analyze each section
        section_analyses = []
        for section in sections_data:
            analysis = self._analyze_section(section, figures, tables)
            section_analyses.append(analysis)

        # Detect which standard sections are present
        detected = {stype: False for stype in STANDARD_SECTIONS}
        for analysis in section_analyses:
            if analysis.detected_type in detected:
                detected[analysis.detected_type] = True

        # Collect issues
        issues = []

        # Check section order
        order_correct, order_issues = self._check_section_order(section_analyses)
        issues.extend(order_issues)

        # Check for missing sections
        issues.extend(self._check_missing_sections(detected))

        # Check balance
        issues.extend(self._check_balance(section_analyses))

        # Check references
        issues.extend(self._check_references(section_analyses, figures, tables))

        # Calculate total word count
        total_words = sum(s.word_count for s in section_analyses)

        # Calculate score
        score = self._calculate_score({
            "detected": detected,
            "order_correct": order_correct,
            "issues": issues,
        })

        return StructureReport(
            total_sections=len(section_analyses),
            total_word_count=total_words,
            detected_sections=detected,
            section_order_correct=order_correct,
            sections=section_analyses,
            issues=issues,
            overall_score=score,
        )

    def suggest_outline(self, paper_spec: dict) -> str:
        """Generate a suggested outline based on analysis."""
        report = self.analyze(paper_spec)

        lines = ["# Paper Structure Outline", ""]

        for section in report.sections:
            status = "✓" if section.word_count > 100 else "△"
            lines.append(f"{status} **{section.name}** ({section.word_count} words)")

            if section.has_figures:
                lines.append(f"  - Figures: {len(section.figure_refs)} referenced")
            if section.has_tables:
                lines.append(f"  - Tables: {len(section.table_refs)} referenced")
            if section.citation_count > 0:
                lines.append(f"  - Citations: {section.citation_count}")

        lines.append("")
        lines.append(f"**Overall Score: {report.overall_score:.0f}/100**")

        if report.issues:
            lines.append("")
            lines.append("## Issues to Address")
            for issue in report.issues:
                icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
                lines.append(f"{icon} {issue.message}")

        return "\n".join(lines)
