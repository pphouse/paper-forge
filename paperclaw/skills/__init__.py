"""
PaperClaw Skills System

Each skill is an independent, composable unit that:
- Has a clear input/output interface
- Can be tested and improved in isolation
- Can be called directly via CLI or composed by orchestrator

Skills:
- spec_parser: Parse and validate paper_spec.yaml
- auto_figure: Generate figures from experiment data
- latex_gen: Generate LaTeX from specification
- pdf_compile: Compile LaTeX to PDF
- qa_citations: Verify citations against external APIs
- qa_figures: Check figure quality and OCR
- qa_structure: Review document structure
- qa_content: LLM-based content review
"""

from .base import Skill, SkillResult, SkillContext
from .registry import SkillRegistry, get_skill, list_skills

__all__ = [
    "Skill",
    "SkillResult",
    "SkillContext",
    "SkillRegistry",
    "get_skill",
    "list_skills",
]
