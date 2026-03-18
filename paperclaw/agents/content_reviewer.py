"""Content Reviewer using LLM for logical analysis.

Uses Claude Code CLI to analyze paper content for:
- Logical inconsistencies between sections
- Claim-evidence alignment
- Missing explanations
- Argumentation flow issues
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ContentIssue:
    """An issue found in paper content."""
    severity: str  # "error", "warning", "info"
    category: str  # "logic", "claim", "flow", "missing", "consistency"
    section: str
    message: str
    suggestion: str = ""
    context: str = ""


@dataclass
class ContentReviewReport:
    """Complete report from content reviewer."""
    sections_reviewed: int
    issues: list[ContentIssue]
    overall_coherence_score: float  # 0-100
    summary: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sections_reviewed": self.sections_reviewed,
            "overall_coherence_score": self.overall_coherence_score,
            "summary": self.summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "section": i.section,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
        }

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


class ContentReviewer:
    """Reviews paper content for logical consistency using LLM.

    Features:
    - Claim-evidence alignment checking
    - Cross-section consistency verification
    - Argumentation flow analysis
    - Missing explanation detection
    - Results-conclusion alignment

    Usage:
        reviewer = ContentReviewer()
        report = reviewer.review(paper_spec)
        print(f"Coherence score: {report.overall_coherence_score}/100")
        for issue in report.issues:
            print(f"[{issue.severity}] {issue.section}: {issue.message}")
    """

    def __init__(
        self,
        use_llm: bool = True,
        language: str = "ja",
        timeout: int = 120,
    ):
        """Initialize content reviewer.

        Args:
            use_llm: Whether to use LLM for deep analysis
            language: Output language ("ja" or "en")
            timeout: LLM call timeout in seconds
        """
        self.use_llm = use_llm
        self.language = language
        self.timeout = timeout

    def _call_claude(self, prompt: str) -> str:
        """Call Claude Code CLI for analysis."""
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={
                    **os.environ,
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                },
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Claude call failed: {result.stderr}")
                return ""
        except subprocess.TimeoutExpired:
            logger.error("Claude call timed out")
            return ""
        except FileNotFoundError:
            logger.error("Claude CLI not found")
            return ""
        except Exception as e:
            logger.error(f"Claude call error: {e}")
            return ""

    def _extract_text(self, content: Any, lang: str = None) -> str:
        """Extract text from bilingual content."""
        lang = lang or self.language
        if isinstance(content, dict):
            return content.get(lang, content.get("en", content.get("ja", "")))
        return str(content) if content else ""

    def _get_full_paper_text(self, paper_spec: dict) -> str:
        """Extract full paper text for analysis."""
        parts = []

        # Title
        meta = paper_spec.get("meta", {})
        title = self._extract_text(meta.get("title", ""))
        if title:
            parts.append(f"# タイトル\n{title}\n")

        # Abstract
        abstract = self._extract_text(paper_spec.get("abstract", ""))
        if abstract:
            parts.append(f"# 概要\n{abstract}\n")

        # Sections
        for section in paper_spec.get("sections", []):
            heading = self._extract_text(section.get("heading", ""))
            content = self._extract_text(section.get("content", ""))

            if heading:
                parts.append(f"## {heading}")
            if content:
                parts.append(content)

            # Subsections
            for subsec in section.get("subsections", []):
                sub_heading = self._extract_text(subsec.get("heading", ""))
                sub_content = self._extract_text(subsec.get("content", ""))
                if sub_heading:
                    parts.append(f"### {sub_heading}")
                if sub_content:
                    parts.append(sub_content)

            parts.append("")

        return "\n".join(parts)

    def _analyze_with_llm(self, paper_text: str) -> dict:
        """Use LLM to analyze paper content."""
        prompt = f"""以下の学術論文を分析し、論理的な問題点を特定してください。

## 分析対象の論文:
{paper_text[:8000]}  # Limit to avoid token limits

## 分析項目:
1. **論理的一貫性**: セクション間で矛盾する主張がないか
2. **主張と根拠の整合性**: 主張が適切な証拠で裏付けられているか
3. **議論の流れ**: 論理的な流れが維持されているか
4. **欠落している説明**: 読者が理解するために必要な説明が抜けていないか
5. **結果と結論の整合性**: 結果が結論を適切にサポートしているか

## 出力形式 (JSON):
{{
  "coherence_score": <0-100の整数>,
  "summary": "<全体的な評価の要約>",
  "strengths": ["<強み1>", "<強み2>"],
  "weaknesses": ["<弱み1>", "<弱み2>"],
  "issues": [
    {{
      "severity": "error|warning|info",
      "category": "logic|claim|flow|missing|consistency",
      "section": "<該当セクション名>",
      "message": "<問題の説明>",
      "suggestion": "<改善提案>"
    }}
  ]
}}

JSON形式のみで回答してください。"""

        response = self._call_claude(prompt)
        if not response:
            return {}

        # Parse JSON from response
        try:
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")

        return {}

    def _rule_based_checks(self, paper_spec: dict) -> list[ContentIssue]:
        """Perform rule-based content checks."""
        issues = []

        # Check abstract vs conclusion alignment
        abstract = self._extract_text(paper_spec.get("abstract", ""))
        conclusion = ""
        for section in paper_spec.get("sections", []):
            heading = self._extract_text(section.get("heading", "")).lower()
            if "conclusion" in heading or "結論" in heading or "まとめ" in heading:
                conclusion = self._extract_text(section.get("content", ""))
                break

        if abstract and conclusion:
            # Check if key terms in abstract appear in conclusion
            abstract_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', abstract.lower()))
            conclusion_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', conclusion.lower()))

            common_important = abstract_words & conclusion_words
            if len(common_important) < len(abstract_words) * 0.2:
                issues.append(ContentIssue(
                    severity="warning",
                    category="consistency",
                    section="Abstract/Conclusion",
                    message="概要と結論で使用されている用語の一貫性が低い可能性があります",
                    suggestion="概要で述べた主要な主張が結論で適切に言及されているか確認してください",
                ))

        # Check for methods section
        has_methods = False
        has_results = False
        for section in paper_spec.get("sections", []):
            heading = self._extract_text(section.get("heading", "")).lower()
            if any(kw in heading for kw in ["method", "手法", "方法", "approach"]):
                has_methods = True
            if any(kw in heading for kw in ["result", "結果", "evaluation", "評価"]):
                has_results = True

        if has_results and not has_methods:
            issues.append(ContentIssue(
                severity="warning",
                category="missing",
                section="Methods",
                message="結果セクションがありますが、手法セクションが見つかりません",
                suggestion="結果を示す前に、使用した手法を明確に説明するセクションを追加してください",
            ))

        # Check for empty or very short sections
        for section in paper_spec.get("sections", []):
            heading = self._extract_text(section.get("heading", ""))
            content = self._extract_text(section.get("content", ""))
            word_count = len(content.split())

            if word_count < 50:
                issues.append(ContentIssue(
                    severity="info",
                    category="missing",
                    section=heading,
                    message=f"セクション「{heading}」の内容が非常に短いです（{word_count}語）",
                    suggestion="このセクションにより詳細な説明を追加することを検討してください",
                ))

        # Check for claims without evidence markers
        evidence_markers = [
            "table", "figure", "fig.", "表", "図",
            "result", "show", "demonstrate", "indicate",
            "結果", "示す", "表す", "明らか",
        ]

        for section in paper_spec.get("sections", []):
            heading = self._extract_text(section.get("heading", "")).lower()
            content = self._extract_text(section.get("content", "")).lower()

            # Skip methods section
            if any(kw in heading for kw in ["method", "手法", "方法"]):
                continue

            # Check for claim patterns without evidence
            claim_patterns = [
                r"we achieve",
                r"our (method|approach|model) (outperform|achieve)",
                r"(significantly|substantially) (better|improve)",
                r"本手法は.*達成",
                r"提案手法.*上回",
            ]

            for pattern in claim_patterns:
                if re.search(pattern, content):
                    has_evidence = any(marker in content for marker in evidence_markers)
                    if not has_evidence:
                        issues.append(ContentIssue(
                            severity="info",
                            category="claim",
                            section=self._extract_text(section.get("heading", "")),
                            message="主張がありますが、図表や具体的な結果への参照が見つかりません",
                            suggestion="主張を裏付ける具体的なデータや図表への参照を追加してください",
                        ))
                    break

        return issues

    def review(self, paper_spec: dict) -> ContentReviewReport:
        """Review paper content for logical issues.

        Args:
            paper_spec: Paper specification dict

        Returns:
            ContentReviewReport with analysis results
        """
        sections = paper_spec.get("sections", [])
        issues = []

        # Rule-based checks (always run)
        issues.extend(self._rule_based_checks(paper_spec))

        # LLM-based analysis (if enabled)
        llm_result = {}
        if self.use_llm:
            paper_text = self._get_full_paper_text(paper_spec)
            if paper_text:
                llm_result = self._analyze_with_llm(paper_text)

                # Add LLM-detected issues
                for issue_data in llm_result.get("issues", []):
                    issues.append(ContentIssue(
                        severity=issue_data.get("severity", "info"),
                        category=issue_data.get("category", "logic"),
                        section=issue_data.get("section", ""),
                        message=issue_data.get("message", ""),
                        suggestion=issue_data.get("suggestion", ""),
                    ))

        # Calculate score
        if llm_result and "coherence_score" in llm_result:
            score = llm_result["coherence_score"]
        else:
            # Calculate based on issues
            score = 100
            for issue in issues:
                if issue.severity == "error":
                    score -= 15
                elif issue.severity == "warning":
                    score -= 5
                elif issue.severity == "info":
                    score -= 1
            score = max(0, min(100, score))

        return ContentReviewReport(
            sections_reviewed=len(sections),
            issues=issues,
            overall_coherence_score=score,
            summary=llm_result.get("summary", "ルールベースのチェックのみ実行しました。"),
            strengths=llm_result.get("strengths", []),
            weaknesses=llm_result.get("weaknesses", []),
        )

    def review_section_pair(
        self,
        section1: dict,
        section2: dict,
        relationship: str = "sequence",
    ) -> list[ContentIssue]:
        """Review consistency between two specific sections.

        Args:
            section1: First section dict
            section2: Second section dict
            relationship: Expected relationship ("sequence", "support", "contrast")

        Returns:
            List of ContentIssue for the section pair
        """
        issues = []

        heading1 = self._extract_text(section1.get("heading", ""))
        heading2 = self._extract_text(section2.get("heading", ""))
        content1 = self._extract_text(section1.get("content", ""))
        content2 = self._extract_text(section2.get("content", ""))

        if not self.use_llm:
            return issues

        prompt = f"""以下の2つのセクション間の論理的な関係を分析してください。

## セクション1: {heading1}
{content1[:2000]}

## セクション2: {heading2}
{content2[:2000]}

## 期待される関係: {relationship}

## 分析項目:
1. 2つのセクション間に矛盾はないか
2. 論理的なつながりは適切か
3. 必要な情報の欠落はないか

問題点があれば、以下のJSON形式で出力してください:
{{
  "issues": [
    {{
      "severity": "error|warning|info",
      "message": "<問題の説明>",
      "suggestion": "<改善提案>"
    }}
  ]
}}

問題がなければ空の配列を返してください: {{"issues": []}}"""

        response = self._call_claude(prompt)
        if not response:
            return issues

        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                for issue_data in result.get("issues", []):
                    issues.append(ContentIssue(
                        severity=issue_data.get("severity", "info"),
                        category="consistency",
                        section=f"{heading1} ↔ {heading2}",
                        message=issue_data.get("message", ""),
                        suggestion=issue_data.get("suggestion", ""),
                    ))
        except json.JSONDecodeError:
            pass

        return issues

    def suggest_improvements(self, report: ContentReviewReport) -> list[str]:
        """Generate improvement suggestions based on report."""
        suggestions = []

        # Priority issues first
        for issue in sorted(report.issues, key=lambda x: {"error": 0, "warning": 1, "info": 2}[x.severity]):
            if issue.suggestion:
                prefix = {"error": "緊急", "warning": "推奨", "info": "検討"}[issue.severity]
                suggestions.append(f"[{prefix}] {issue.section}: {issue.suggestion}")

        # Add general suggestions based on weaknesses
        for weakness in report.weaknesses:
            suggestions.append(f"[改善点] {weakness}")

        if report.overall_coherence_score < 70:
            suggestions.insert(0, "論理的一貫性に大きな問題があります。全体的な構成を見直してください。")

        return suggestions
