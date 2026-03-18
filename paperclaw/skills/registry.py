"""Skill registry for discovering and loading skills."""

from __future__ import annotations

from typing import Type, Optional
from .base import Skill


class SkillRegistry:
    """Registry for managing skills.

    Usage:
        registry = SkillRegistry()
        registry.register(MySkill)
        skill = registry.get("my-skill")
        result = skill.run(context)
    """

    _instance: Optional["SkillRegistry"] = None
    _skills: dict[str, Type[Skill]]

    def __new__(cls) -> "SkillRegistry":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
        return cls._instance

    def register(self, skill_class: Type[Skill]) -> None:
        """Register a skill class."""
        # Create instance to get name
        instance = skill_class()
        self._skills[instance.name] = skill_class

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill instance by name."""
        skill_class = self._skills.get(name)
        if skill_class:
            return skill_class()
        return None

    def list(self) -> list[dict]:
        """List all registered skills."""
        result = []
        for name, skill_class in self._skills.items():
            instance = skill_class()
            result.append({
                "name": instance.name,
                "description": instance.description,
                "version": instance.version,
                "dependencies": instance.get_dependencies(),
            })
        return result

    def clear(self) -> None:
        """Clear all registered skills (for testing)."""
        self._skills = {}


# Global registry instance
_registry = SkillRegistry()


def register_skill(skill_class: Type[Skill]) -> Type[Skill]:
    """Decorator to register a skill."""
    _registry.register(skill_class)
    return skill_class


def get_skill(name: str) -> Optional[Skill]:
    """Get a skill by name."""
    return _registry.get(name)


def list_skills() -> list[dict]:
    """List all registered skills."""
    return _registry.list()


def load_all_skills() -> None:
    """Load all built-in skills."""
    # Import skill modules to trigger registration
    from . import (
        spec_parser,
        auto_figure,
        latex_gen,
        pdf_compile,
        qa_citations,
        qa_figures,
        qa_structure,
    )
