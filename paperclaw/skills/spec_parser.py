"""Spec Parser Skill - Parse and validate paper_spec.yaml."""

from __future__ import annotations

from pathlib import Path
import yaml

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@register_skill
class SpecParserSkill(Skill):
    """Parse and validate paper specification files.

    Input:
        - project_dir with paper_spec.yaml

    Output:
        - Parsed and validated specification
        - Validation warnings/errors
    """

    @property
    def name(self) -> str:
        return "spec-parser"

    @property
    def description(self) -> str:
        return "Parse and validate paper_spec.yaml"

    def validate_input(self, context: SkillContext) -> list[str]:
        errors = super().validate_input(context)
        spec_path = context.project_dir / "paper_spec.yaml"
        if not spec_path.exists():
            errors.append(f"paper_spec.yaml not found in {context.project_dir}")
        return errors

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)
        spec_path = context.project_dir / "paper_spec.yaml"

        # Parse YAML
        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            result.status = SkillStatus.ERROR
            result.add_error(f"YAML parse error: {e}")
            return result

        # Validate structure
        validation = self._validate_spec(spec)
        result.data["spec"] = spec
        result.data["validation"] = validation

        if validation["errors"]:
            result.status = SkillStatus.ERROR
            result.errors.extend(validation["errors"])
        elif validation["warnings"]:
            result.status = SkillStatus.WARNING
            result.messages.extend(validation["warnings"])
        else:
            result.add_message("Specification is valid")

        # Collect metrics
        result.metrics["sections"] = len(spec.get("sections", []))
        result.metrics["figures"] = len(spec.get("figures", {}))
        result.metrics["tables"] = len(spec.get("tables", {}))
        result.metrics["references"] = len(spec.get("references", []))

        return result

    def _validate_spec(self, spec: dict) -> dict:
        """Validate specification structure."""
        errors = []
        warnings = []

        # Required fields
        meta = spec.get("meta", {})
        if not meta.get("title"):
            errors.append("Missing meta.title")

        if not spec.get("abstract"):
            warnings.append("Missing abstract")

        if not spec.get("sections"):
            errors.append("No sections defined")

        # Check sections
        for i, section in enumerate(spec.get("sections", [])):
            if not section.get("heading"):
                errors.append(f"Section {i+1}: missing heading")
            if not section.get("content"):
                warnings.append(f"Section {i+1}: missing content")

        # Check figures
        figures = spec.get("figures", {})
        if isinstance(figures, dict):
            for fig_id, fig in figures.items():
                if not fig.get("path"):
                    warnings.append(f"Figure {fig_id}: missing path")
                if not fig.get("caption"):
                    warnings.append(f"Figure {fig_id}: missing caption")

        # Check references
        for i, ref in enumerate(spec.get("references", [])):
            if not ref.get("title"):
                warnings.append(f"Reference {i+1}: missing title")

        return {"errors": errors, "warnings": warnings}
