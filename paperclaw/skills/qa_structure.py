"""QA Structure Skill - Review document structure and organization."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@dataclass
class StructureIssue:
    """A structural issue found in the paper."""
    severity: str  # "error", "warning", "info"
    category: str  # "sections", "figures", "references", "abstract"
    message: str
    suggestion: str = ""


@register_skill
class QaStructureSkill(Skill):
    """Review document structure and organization.

    Input:
        - Paper specification

    Output:
        - Structure score
        - List of structural issues
        - Suggestions for improvement
    """

    # Expected sections (in order)
    EXPECTED_SECTIONS = [
        ("introduction", ["introduction", "はじめに", "序論"]),
        ("related_work", ["related work", "関連研究", "background", "背景"]),
        ("methods", ["method", "methods", "methodology", "手法", "提案手法"]),
        ("results", ["result", "results", "experiment", "実験", "結果"]),
        ("discussion", ["discussion", "考察", "議論"]),
        ("conclusion", ["conclusion", "conclusions", "結論", "おわりに"]),
    ]

    @property
    def name(self) -> str:
        return "qa-structure"

    @property
    def description(self) -> str:
        return "Review document structure and organization"

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)
        issues: list[StructureIssue] = []

        spec = context.spec
        language = context.language

        # Check sections
        section_issues = self._check_sections(spec, language)
        issues.extend(section_issues)

        # Check abstract
        abstract_issues = self._check_abstract(spec, language)
        issues.extend(abstract_issues)

        # Check figures
        figure_issues = self._check_figure_references(spec, language)
        issues.extend(figure_issues)

        # Check tables
        table_issues = self._check_table_references(spec, language)
        issues.extend(table_issues)

        # Check references
        ref_issues = self._check_references(spec)
        issues.extend(ref_issues)

        # Calculate score
        score = self._calculate_score(issues)

        # Compile results
        result.data["issues"] = [vars(i) for i in issues]
        result.data["score"] = score
        result.metrics["score"] = score
        result.metrics["error_count"] = sum(1 for i in issues if i.severity == "error")
        result.metrics["warning_count"] = sum(1 for i in issues if i.severity == "warning")

        if result.metrics["error_count"] > 0:
            result.status = SkillStatus.WARNING

        result.add_message(f"Structure score: {score}/100")
        result.add_message(f"Issues: {len(issues)} ({result.metrics['error_count']} errors, {result.metrics['warning_count']} warnings)")

        return result

    def _check_sections(self, spec: dict, language: str) -> list[StructureIssue]:
        """Check section presence and order."""
        issues = []
        sections = spec.get("sections", [])

        if not sections:
            issues.append(StructureIssue(
                severity="error",
                category="sections",
                message="No sections defined",
                suggestion="Add sections to the paper specification"
            ))
            return issues

        # Get section titles
        section_titles = []
        for section in sections:
            heading = section.get("heading", {})
            if isinstance(heading, dict):
                title = heading.get(language, heading.get("en", ""))
            else:
                title = str(heading)
            section_titles.append(title.lower())

        # Check for expected sections
        found_sections = {}
        for section_type, keywords in self.EXPECTED_SECTIONS:
            found = False
            for i, title in enumerate(section_titles):
                if any(kw in title for kw in keywords):
                    found_sections[section_type] = i
                    found = True
                    break
            if not found:
                issues.append(StructureIssue(
                    severity="warning",
                    category="sections",
                    message=f"Missing section: {section_type}",
                    suggestion=f"Consider adding a {section_type} section"
                ))

        # Check section order
        positions = list(found_sections.values())
        if positions != sorted(positions):
            issues.append(StructureIssue(
                severity="warning",
                category="sections",
                message="Sections may be out of order",
                suggestion="Standard order: Introduction, Related Work, Methods, Results, Discussion, Conclusion"
            ))

        # Check section lengths
        for i, section in enumerate(sections):
            content = section.get("content", {})
            if isinstance(content, dict):
                text = content.get(language, content.get("en", ""))
            else:
                text = str(content)

            word_count = len(text.split())
            if word_count < 50:
                issues.append(StructureIssue(
                    severity="info",
                    category="sections",
                    message=f"Section {i+1} is very short ({word_count} words)",
                    suggestion="Consider expanding the content"
                ))

        return issues

    def _check_abstract(self, spec: dict, language: str) -> list[StructureIssue]:
        """Check abstract presence and length."""
        issues = []
        abstract = spec.get("abstract", {})

        if not abstract:
            issues.append(StructureIssue(
                severity="error",
                category="abstract",
                message="Missing abstract",
                suggestion="Add an abstract to the paper specification"
            ))
            return issues

        if isinstance(abstract, dict):
            text = abstract.get(language, abstract.get("en", ""))
        else:
            text = str(abstract)

        word_count = len(text.split())

        if word_count < 100:
            issues.append(StructureIssue(
                severity="warning",
                category="abstract",
                message=f"Abstract is short ({word_count} words)",
                suggestion="Abstracts typically have 150-300 words"
            ))
        elif word_count > 400:
            issues.append(StructureIssue(
                severity="warning",
                category="abstract",
                message=f"Abstract is long ({word_count} words)",
                suggestion="Consider condensing to under 300 words"
            ))

        return issues

    def _check_figure_references(self, spec: dict, language: str) -> list[StructureIssue]:
        """Check that all figures are referenced in text."""
        issues = []
        figures = spec.get("figures", {})

        if isinstance(figures, list):
            figure_ids = [f.get("id", f"fig_{i}") for i, f in enumerate(figures)]
        else:
            figure_ids = list(figures.keys())

        if not figure_ids:
            return issues

        # Get all text content
        all_text = ""
        for section in spec.get("sections", []):
            content = section.get("content", {})
            if isinstance(content, dict):
                all_text += content.get(language, content.get("en", ""))
            else:
                all_text += str(content)

        # Check each figure is referenced
        for fig_id in figure_ids:
            # Look for Figure X, Fig. X, or fig_id references
            patterns = [
                fig_id,
                fig_id.replace("_", " "),
                f"Figure",
                f"Fig.",
            ]
            found = any(p.lower() in all_text.lower() for p in patterns)
            if not found:
                issues.append(StructureIssue(
                    severity="warning",
                    category="figures",
                    message=f"Figure '{fig_id}' may not be referenced in text",
                    suggestion="Ensure all figures are referenced in the paper body"
                ))

        return issues

    def _check_table_references(self, spec: dict, language: str) -> list[StructureIssue]:
        """Check that all tables are referenced in text."""
        issues = []
        tables = spec.get("tables", {})

        if isinstance(tables, list):
            table_ids = [t.get("id", f"tbl_{i}") for i, t in enumerate(tables)]
        else:
            table_ids = list(tables.keys())

        if not table_ids:
            return issues

        # Get all text content
        all_text = ""
        for section in spec.get("sections", []):
            content = section.get("content", {})
            if isinstance(content, dict):
                all_text += content.get(language, content.get("en", ""))
            else:
                all_text += str(content)

        # Check each table is referenced
        for tbl_id in table_ids:
            patterns = [tbl_id, "Table", "表"]
            found = any(p.lower() in all_text.lower() for p in patterns)
            if not found:
                issues.append(StructureIssue(
                    severity="warning",
                    category="tables",
                    message=f"Table '{tbl_id}' may not be referenced in text",
                    suggestion="Ensure all tables are referenced in the paper body"
                ))

        return issues

    def _check_references(self, spec: dict) -> list[StructureIssue]:
        """Check reference completeness."""
        issues = []
        references = spec.get("references", [])

        if not references:
            issues.append(StructureIssue(
                severity="warning",
                category="references",
                message="No references defined",
                suggestion="Add references to support claims in the paper"
            ))
            return issues

        for i, ref in enumerate(references):
            if not isinstance(ref, dict):
                continue

            if not ref.get("title"):
                issues.append(StructureIssue(
                    severity="warning",
                    category="references",
                    message=f"Reference {i+1}: missing title",
                    suggestion="Add title to reference"
                ))

            if not ref.get("authors") and not ref.get("author"):
                issues.append(StructureIssue(
                    severity="info",
                    category="references",
                    message=f"Reference {i+1}: missing authors",
                    suggestion="Add authors to reference"
                ))

            if not ref.get("year"):
                issues.append(StructureIssue(
                    severity="info",
                    category="references",
                    message=f"Reference {i+1}: missing year",
                    suggestion="Add publication year to reference"
                ))

        return issues

    def _calculate_score(self, issues: list[StructureIssue]) -> int:
        """Calculate structure score based on issues."""
        score = 100

        for issue in issues:
            if issue.severity == "error":
                score -= 15
            elif issue.severity == "warning":
                score -= 5
            elif issue.severity == "info":
                score -= 1

        return max(0, score)
