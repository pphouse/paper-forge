"""Experiment directory scanner and data collector.

Automatically discovers and categorizes files in an experiment directory:
- Data files (CSV, JSON, YAML, TSV, Excel) -> analyzed
- Images (PNG, JPG, SVG) -> listed as potential figures
- Documents (MD, TXT, logs) -> text extracted
- Code files -> listed for context
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


# File extension categories
DATA_EXTENSIONS = {".csv", ".json", ".yaml", ".yml", ".tsv", ".xlsx", ".xls"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".tiff", ".tif", ".bmp", ".gif"}
DOC_EXTENSIONS = {".md", ".txt", ".rst", ".log", ".tex"}
EXTERNAL_DOC_EXTENSIONS = {".docx", ".pdf", ".pptx"}
CODE_EXTENSIONS = {".py", ".r", ".jl", ".m", ".ipynb"}

# Directories to skip
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "node_modules", ".tox",
    ".mypy_cache", ".pytest_cache", ".ipynb_checkpoints",
}


class ExperimentCollector:
    """Scans an experiment directory and collects all relevant files."""

    def __init__(self, experiment_dir: str | Path, max_text_chars: int = 50000):
        self.experiment_dir = Path(experiment_dir).resolve()
        self.max_text_chars = max_text_chars
        if not self.experiment_dir.exists():
            raise FileNotFoundError(f"Experiment directory not found: {experiment_dir}")
        if not self.experiment_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {experiment_dir}")

    def collect(self) -> dict[str, Any]:
        """Scan directory and categorize all files.

        Returns:
            Dict with keys: data_files, images, documents, code_files,
            tree, text_contents
        """
        result: dict[str, Any] = {
            "data_files": [],
            "images": [],
            "documents": [],
            "code_files": [],
            "other_files": [],
            "tree": "",
            "text_contents": {},
        }

        all_files = self._walk_files()

        for f in all_files:
            ext = f.suffix.lower()
            if ext in DATA_EXTENSIONS:
                result["data_files"].append(f)
            elif ext in IMAGE_EXTENSIONS:
                result["images"].append(f)
            elif ext in DOC_EXTENSIONS or ext in EXTERNAL_DOC_EXTENSIONS:
                result["documents"].append(f)
            elif ext in CODE_EXTENSIONS:
                result["code_files"].append(f)
            else:
                result["other_files"].append(f)

        result["tree"] = self._build_tree()

        # Extract text from in-directory text documents
        total_chars = 0
        for doc in result["documents"]:
            if total_chars >= self.max_text_chars:
                break
            ext = doc.suffix.lower()
            if ext in EXTERNAL_DOC_EXTENSIONS:
                # These need special extractors - handled by doc_extractor
                continue
            try:
                text = doc.read_text(encoding="utf-8", errors="replace")
                budget = self.max_text_chars - total_chars
                truncated = text[:budget]
                rel = str(doc.relative_to(self.experiment_dir))
                result["text_contents"][rel] = truncated
                total_chars += len(truncated)
            except Exception:
                pass

        # Also pick up README at root
        for name in ("README.md", "README.txt", "README", "readme.md"):
            readme = self.experiment_dir / name
            rel = name
            if readme.exists() and rel not in result["text_contents"]:
                try:
                    text = readme.read_text(encoding="utf-8", errors="replace")
                    result["text_contents"][rel] = text[:5000]
                except Exception:
                    pass

        return result

    # ------------------------------------------------------------------

    def _walk_files(self) -> list[Path]:
        files: list[Path] = []
        for item in sorted(self.experiment_dir.rglob("*")):
            parts = item.relative_to(self.experiment_dir).parts
            if any(p.startswith(".") or p in SKIP_DIRS or "egg-info" in p for p in parts):
                continue
            if item.is_file() and item.stat().st_size > 0:
                files.append(item)
        return files

    def _build_tree(self, max_depth: int = 4) -> str:
        lines = [self.experiment_dir.name + "/"]
        self._tree_recurse(self.experiment_dir, "", lines, 0, max_depth)
        return "\n".join(lines[:200])

    def _tree_recurse(
        self, path: Path, prefix: str, lines: list[str], depth: int, max_depth: int
    ) -> None:
        if depth >= max_depth or len(lines) >= 200:
            return
        entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        entries = [e for e in entries
                   if not e.name.startswith(".") and e.name not in SKIP_DIRS]

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            ext_prefix = "    " if is_last else "│   "

            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                self._tree_recurse(entry, prefix + ext_prefix, lines, depth + 1, max_depth)
            else:
                size = entry.stat().st_size
                if size >= 1024 * 1024:
                    size_str = f"{size / (1024*1024):.1f}MB"
                elif size >= 1024:
                    size_str = f"{size / 1024:.0f}KB"
                else:
                    size_str = f"{size}B"
                lines.append(f"{prefix}{connector}{entry.name} ({size_str})")

    # ------------------------------------------------------------------
    # Convenience: summarise collection for prompts
    # ------------------------------------------------------------------

    def summarise(self, collected: dict[str, Any]) -> str:
        """Produce a human-readable summary of collected materials."""
        parts: list[str] = []

        parts.append(f"## Experiment Directory Structure\n```\n{collected['tree']}\n```")

        if collected["data_files"]:
            items = [str(f.relative_to(self.experiment_dir)) for f in collected["data_files"]]
            parts.append(f"## Data Files ({len(items)})\n" + "\n".join(f"- {i}" for i in items))

        if collected["images"]:
            items = [str(f.relative_to(self.experiment_dir)) for f in collected["images"]]
            parts.append(f"## Images ({len(items)})\n" + "\n".join(f"- {i}" for i in items))

        if collected["code_files"]:
            items = [str(f.relative_to(self.experiment_dir)) for f in collected["code_files"]]
            parts.append(f"## Code Files ({len(items)})\n" + "\n".join(f"- {i}" for i in items))

        if collected["text_contents"]:
            parts.append("## Extracted Text from Documents")
            for fname, text in collected["text_contents"].items():
                parts.append(f"\n### {fname}\n{text}")

        return "\n\n".join(parts)
