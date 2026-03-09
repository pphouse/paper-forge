"""Data models for PaperForge paper specifications."""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class BilingualText:
    """Text with English and Japanese versions."""
    en: str = ""
    ja: str = ""

    def get(self, lang: str) -> str:
        return getattr(self, lang, self.en)

    def to_dict(self) -> dict:
        return {"en": self.en, "ja": self.ja}

    @classmethod
    def from_value(cls, value) -> BilingualText:
        if isinstance(value, dict):
            return cls(en=value.get("en", ""), ja=value.get("ja", ""))
        if isinstance(value, str):
            return cls(en=value, ja=value)
        return cls()


@dataclass
class Author:
    name: str = ""
    affiliation: str = ""
    email: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FigureSpec:
    path: str = ""
    caption: BilingualText = field(default_factory=BilingualText)
    label: str = ""
    wide: bool = False

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "caption": self.caption.to_dict(),
            "label": self.label,
            "wide": self.wide,
        }

    @classmethod
    def from_dict(cls, d: dict) -> FigureSpec:
        return cls(
            path=d.get("path", ""),
            caption=BilingualText.from_value(d.get("caption", {})),
            label=d.get("label", ""),
            wide=d.get("wide", False),
        )


@dataclass
class TableSpec:
    caption: BilingualText = field(default_factory=BilingualText)
    label: str = ""
    columns: list[str] = field(default_factory=list)
    data: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "caption": self.caption.to_dict(),
            "label": self.label,
            "columns": self.columns,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TableSpec:
        return cls(
            caption=BilingualText.from_value(d.get("caption", {})),
            label=d.get("label", ""),
            columns=d.get("columns", []),
            data=d.get("data", []),
        )


@dataclass
class Section:
    heading: BilingualText = field(default_factory=BilingualText)
    content: BilingualText = field(default_factory=BilingualText)
    figures: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    subsections: list[Section] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "heading": self.heading.to_dict(),
            "content": self.content.to_dict(),
        }
        if self.figures:
            d["figures"] = self.figures
        if self.tables:
            d["tables"] = self.tables
        if self.subsections:
            d["subsections"] = [s.to_dict() for s in self.subsections]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Section:
        return cls(
            heading=BilingualText.from_value(d.get("heading", {})),
            content=BilingualText.from_value(d.get("content", {})),
            figures=d.get("figures", []),
            tables=d.get("tables", []),
            subsections=[Section.from_dict(s) for s in d.get("subsections", [])],
        )


@dataclass
class Reference:
    key: str = ""
    authors: str = ""
    title: str = ""
    journal: str = ""
    year: int = 0
    doi: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PaperSpec:
    """Complete paper specification."""
    meta: dict = field(default_factory=lambda: {
        "title": {"en": "", "ja": ""},
        "template": "twocol",
        "date": "",
    })
    authors: list[Author] = field(default_factory=list)
    keywords: BilingualText = field(default_factory=BilingualText)
    abstract: BilingualText = field(default_factory=BilingualText)
    sections: list[Section] = field(default_factory=list)
    figures: dict[str, FigureSpec] = field(default_factory=dict)
    tables: dict[str, TableSpec] = field(default_factory=dict)
    references: list[Reference] = field(default_factory=list)
    acknowledgments: BilingualText = field(default_factory=BilingualText)

    def to_dict(self) -> dict:
        return {
            "meta": self.meta,
            "authors": [a.to_dict() for a in self.authors],
            "keywords": self.keywords.to_dict(),
            "abstract": self.abstract.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
            "figures": {k: v.to_dict() for k, v in self.figures.items()},
            "tables": {k: v.to_dict() for k, v in self.tables.items()},
            "references": [r.to_dict() for r in self.references],
            "acknowledgments": self.acknowledgments.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> PaperSpec:
        return cls(
            meta=d.get("meta", {}),
            authors=[Author(**a) for a in d.get("authors", [])],
            keywords=BilingualText.from_value(d.get("keywords", {})),
            abstract=BilingualText.from_value(d.get("abstract", {})),
            sections=[Section.from_dict(s) for s in d.get("sections", [])],
            figures={k: FigureSpec.from_dict(v) for k, v in d.get("figures", {}).items()},
            tables={k: TableSpec.from_dict(v) for k, v in d.get("tables", {}).items()},
            references=[Reference(**r) for r in d.get("references", [])],
            acknowledgments=BilingualText.from_value(d.get("acknowledgments", {})),
        )

    def save(self, path: str | Path):
        """Save spec to YAML file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    @classmethod
    def load(cls, path: str | Path) -> PaperSpec:
        """Load spec from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    @classmethod
    def create_template(cls, title_en: str = "", title_ja: str = "",
                        template: str = "twocol") -> PaperSpec:
        """Create a new paper spec with standard academic structure."""
        standard_sections = [
            Section(
                heading=BilingualText(en="Introduction", ja="はじめに"),
                content=BilingualText(
                    en="Describe the background and motivation of your research.",
                    ja="研究の背景と動機を記述してください。",
                ),
            ),
            Section(
                heading=BilingualText(en="Methods", ja="手法"),
                content=BilingualText(
                    en="Describe your methodology.",
                    ja="手法を記述してください。",
                ),
                subsections=[
                    Section(
                        heading=BilingualText(en="Dataset", ja="データセット"),
                        content=BilingualText(en="", ja=""),
                    ),
                    Section(
                        heading=BilingualText(en="Model", ja="モデル"),
                        content=BilingualText(en="", ja=""),
                    ),
                ],
            ),
            Section(
                heading=BilingualText(en="Results", ja="結果"),
                content=BilingualText(
                    en="Present your findings.",
                    ja="結果を提示してください。",
                ),
            ),
            Section(
                heading=BilingualText(en="Discussion", ja="考察"),
                content=BilingualText(
                    en="Discuss the implications of your results.",
                    ja="結果の意義を考察してください。",
                ),
            ),
            Section(
                heading=BilingualText(en="Conclusion", ja="結論"),
                content=BilingualText(
                    en="Summarize your findings and future work.",
                    ja="結論と今後の課題を記述してください。",
                ),
            ),
        ]

        return cls(
            meta={
                "title": {"en": title_en or "Untitled Paper", "ja": title_ja or "無題の論文"},
                "template": template,
                "date": "",
            },
            sections=standard_sections,
        )
