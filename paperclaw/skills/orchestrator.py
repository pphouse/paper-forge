"""Orchestrator - Compose and execute skill pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable
import time

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import get_skill, load_all_skills


@dataclass
class PipelineStep:
    """A step in the pipeline."""
    skill_name: str
    config: dict = field(default_factory=dict)
    condition: Optional[Callable[[dict], bool]] = None  # Skip if returns False
    on_error: str = "continue"  # "continue", "stop", "skip_remaining"


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    status: SkillStatus
    results: dict[str, SkillResult]
    total_duration_ms: float
    steps_completed: int
    steps_skipped: int
    steps_failed: int

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "results": {k: v.to_dict() for k, v in self.results.items()},
            "total_duration_ms": self.total_duration_ms,
            "steps_completed": self.steps_completed,
            "steps_skipped": self.steps_skipped,
            "steps_failed": self.steps_failed,
        }


class Orchestrator:
    """Orchestrates execution of skill pipelines.

    Usage:
        orchestrator = Orchestrator()

        # Define pipeline
        pipeline = [
            PipelineStep("spec-parser"),
            PipelineStep("auto-figure", config={"data_dir": "experiments"}),
            PipelineStep("latex-gen"),
            PipelineStep("pdf-compile"),
        ]

        # Execute
        result = orchestrator.run(pipeline, context)
    """

    def __init__(self):
        # Ensure skills are loaded
        load_all_skills()

    def run(
        self,
        steps: list[PipelineStep],
        context: SkillContext,
        verbose: bool = False,
    ) -> PipelineResult:
        """Execute a pipeline of skills.

        Args:
            steps: List of pipeline steps to execute
            context: Execution context
            verbose: Enable verbose output

        Returns:
            PipelineResult with all skill results
        """
        start_time = time.time()
        results: dict[str, SkillResult] = {}
        completed = 0
        skipped = 0
        failed = 0
        overall_status = SkillStatus.SUCCESS

        # Track data flow between skills
        shared_data = {}

        for step in steps:
            # Check condition
            if step.condition and not step.condition(shared_data):
                skipped += 1
                if verbose:
                    print(f"[SKIP] {step.skill_name}")
                continue

            # Get skill
            skill = get_skill(step.skill_name)
            if not skill:
                failed += 1
                results[step.skill_name] = SkillResult(
                    status=SkillStatus.ERROR,
                    errors=[f"Skill not found: {step.skill_name}"]
                )
                if step.on_error == "stop":
                    overall_status = SkillStatus.ERROR
                    break
                continue

            # Update context with step config
            step_context = SkillContext(
                project_dir=context.project_dir,
                spec=context.spec,
                language=context.language,
                verbose=verbose,
                cache_dir=context.cache_dir,
                config={**context.config, **step.config, **shared_data},
            )

            # Update spec if it was parsed
            if "spec" in shared_data:
                step_context.spec = shared_data["spec"]

            if verbose:
                print(f"[RUN] {step.skill_name}...")

            # Execute skill
            result = skill.run(step_context)
            results[step.skill_name] = result

            # Update shared data
            if result.data:
                shared_data.update(result.data)

            if result.success:
                completed += 1
                if verbose:
                    print(f"[OK] {step.skill_name} ({result.metrics.get('duration_ms', 0):.0f}ms)")
            else:
                failed += 1
                if verbose:
                    print(f"[FAIL] {step.skill_name}: {result.errors}")

                if result.status == SkillStatus.ERROR:
                    if step.on_error == "stop":
                        overall_status = SkillStatus.ERROR
                        break
                    elif step.on_error == "skip_remaining":
                        overall_status = SkillStatus.WARNING
                        break
                    else:
                        overall_status = SkillStatus.WARNING

        total_duration = (time.time() - start_time) * 1000

        return PipelineResult(
            status=overall_status,
            results=results,
            total_duration_ms=round(total_duration, 2),
            steps_completed=completed,
            steps_skipped=skipped,
            steps_failed=failed,
        )

    # Predefined pipelines
    @staticmethod
    def build_pipeline() -> list[PipelineStep]:
        """Pipeline for building PDF from spec."""
        return [
            PipelineStep("spec-parser", on_error="stop"),
            PipelineStep("latex-gen", on_error="stop"),
            PipelineStep("pdf-compile", on_error="stop"),
        ]

    @staticmethod
    def qa_pipeline() -> list[PipelineStep]:
        """Pipeline for quality assurance checks."""
        return [
            PipelineStep("spec-parser", on_error="stop"),
            PipelineStep("qa-structure"),
            PipelineStep("qa-figures"),
            PipelineStep("qa-citations"),
        ]

    @staticmethod
    def full_pipeline() -> list[PipelineStep]:
        """Full pipeline: build + QA."""
        return [
            PipelineStep("spec-parser", on_error="stop"),
            PipelineStep("auto-figure"),
            PipelineStep("latex-gen", on_error="stop"),
            PipelineStep("pdf-compile", on_error="stop"),
            PipelineStep("qa-structure"),
            PipelineStep("qa-figures"),
            PipelineStep("qa-citations"),
        ]
