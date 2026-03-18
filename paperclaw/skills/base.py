"""Base classes for PaperClaw skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
import json
import yaml
import time


class SkillStatus(Enum):
    """Skill execution status."""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class SkillResult:
    """Result of skill execution.

    Attributes:
        status: Execution status
        data: Output data (skill-specific)
        messages: Human-readable messages/logs
        errors: Error messages if any
        metrics: Performance metrics
        artifacts: Paths to generated files
    """
    status: SkillStatus
    data: dict = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "data": self.data,
            "messages": self.messages,
            "errors": self.errors,
            "metrics": self.metrics,
            "artifacts": [str(p) for p in self.artifacts],
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status in (SkillStatus.SUCCESS, SkillStatus.WARNING)

    def add_message(self, msg: str) -> None:
        """Add a message."""
        self.messages.append(msg)

    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)
        if self.status == SkillStatus.SUCCESS:
            self.status = SkillStatus.WARNING


@dataclass
class SkillContext:
    """Context passed to skills.

    Attributes:
        project_dir: Project directory path
        spec: Parsed paper specification
        language: Target language (en, ja)
        verbose: Enable verbose output
        cache_dir: Cache directory for intermediate results
        config: Skill-specific configuration
    """
    project_dir: Path
    spec: dict = field(default_factory=dict)
    language: str = "en"
    verbose: bool = False
    cache_dir: Optional[Path] = None
    config: dict = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.project_dir, str):
            self.project_dir = Path(self.project_dir)
        if self.cache_dir is None:
            self.cache_dir = self.project_dir / ".paperclaw_cache"
        elif isinstance(self.cache_dir, str):
            self.cache_dir = Path(self.cache_dir)

    @classmethod
    def from_project(cls, project_dir: str | Path, **kwargs) -> "SkillContext":
        """Create context from project directory."""
        project_dir = Path(project_dir)
        spec_path = project_dir / "paper_spec.yaml"

        spec = {}
        if spec_path.exists():
            with open(spec_path, encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}

        return cls(project_dir=project_dir, spec=spec, **kwargs)


class Skill(ABC):
    """Base class for all skills.

    Each skill must implement:
    - name: Unique skill identifier
    - description: Human-readable description
    - execute(): Main execution logic

    Optional overrides:
    - validate_input(): Validate context before execution
    - get_dependencies(): Return list of required skills
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @property
    def version(self) -> str:
        """Skill version."""
        return "1.0.0"

    def validate_input(self, context: SkillContext) -> list[str]:
        """Validate input context.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        if not context.project_dir.exists():
            errors.append(f"Project directory not found: {context.project_dir}")
        return errors

    def get_dependencies(self) -> list[str]:
        """Return list of skill names this skill depends on."""
        return []

    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill.

        Args:
            context: Skill execution context

        Returns:
            SkillResult with execution results
        """
        pass

    def run(self, context: SkillContext) -> SkillResult:
        """Run the skill with timing and error handling.

        This is the main entry point that wraps execute() with:
        - Input validation
        - Timing metrics
        - Error handling
        """
        start_time = time.time()

        # Validate input
        validation_errors = self.validate_input(context)
        if validation_errors:
            return SkillResult(
                status=SkillStatus.ERROR,
                errors=validation_errors,
                metrics={"duration_ms": 0}
            )

        try:
            result = self.execute(context)
        except Exception as e:
            result = SkillResult(
                status=SkillStatus.ERROR,
                errors=[f"Skill execution failed: {str(e)}"]
            )

        # Add timing
        duration_ms = (time.time() - start_time) * 1000
        result.metrics["duration_ms"] = round(duration_ms, 2)
        result.metrics["skill_name"] = self.name
        result.metrics["skill_version"] = self.version

        return result

    def __repr__(self) -> str:
        return f"<Skill:{self.name} v{self.version}>"
