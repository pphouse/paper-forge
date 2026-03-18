"""AI-powered text generation for PaperClaw.

Supports multiple backends:
- Claude Code CLI (`claude -p`) - default, no API key needed
- Azure OpenAI API - for production use

Set PAPERFORGE_BACKEND=azure to use Azure OpenAI, otherwise Claude Code is used.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from openai import AzureOpenAI
except ImportError:
    AzureOpenAI = None  # type: ignore[assignment,misc]

from .models import (
    PaperSpec,
    BilingualText,
    Section,
    Author,
    FigureSpec,
    TableSpec,
    Reference,
)


class TextGenerationError(Exception):
    """Raised when AI text generation fails."""
    pass


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert academic paper writer. Given a research overview and data analysis results,
you generate a complete academic paper draft in strict JSON format.

IMPORTANT RULES:
- Write in formal academic style appropriate for peer-reviewed journals
- Use passive voice for Methods sections
- Use hedging language (e.g., "suggests", "indicates") in Discussion
- Be precise with numbers and cite data analysis results accurately
- Generate BOTH English and Japanese text for every text field
- Japanese text should be natural academic Japanese, not machine translation
- Return ONLY valid JSON with no commentary before or after

OUTPUT JSON SCHEMA:
{
  "abstract": {"en": "...", "ja": "..."},
  "keywords": {"en": "keyword1, keyword2, ...", "ja": "キーワード1, キーワード2, ..."},
  "sections": [
    {
      "heading": {"en": "Introduction", "ja": "はじめに"},
      "content": {"en": "...", "ja": "..."},
      "figures": ["fig_accuracy_bar"],
      "subsections": [
        {"heading": {"en": "...", "ja": "..."}, "content": {"en": "...", "ja": "..."}}
      ]
    }
  ],
  "data_figures": {
    "fig_accuracy_bar": {
      "type": "bar",
      "data": {"labels": ["CNN", "RNN", "Transformer"], "values": [0.92, 0.88, 0.95]},
      "title": "Model Accuracy Comparison",
      "xlabel": "Model",
      "ylabel": "Accuracy",
      "figsize": [6, 4],
      "caption": {"en": "Comparison of model accuracies", "ja": "モデル精度の比較"},
      "label": "fig:accuracy"
    }
  },
  "diagrams": {
    "fig_pipeline": {
      "mermaid": "graph LR; A[Raw Data] --> B[Preprocessing]; B --> C[Model]; C --> D[Evaluation]",
      "caption": {"en": "Processing pipeline overview", "ja": "処理パイプラインの概要"},
      "label": "fig:pipeline"
    }
  },
  "tables": {
    "tab1": {
      "caption": {"en": "...", "ja": "..."},
      "label": "tab:xxx",
      "columns": ["Col1", "Col2"],
      "data": [["val1", "val2"]]
    }
  },
  "references": [
    {"key": "author2024", "authors": "A. Author et al.", "title": "Paper Title", "journal": "Journal Name", "year": 2024}
  ],
  "acknowledgments": {"en": "...", "ja": "..."}
}

DATA FIGURES GUIDELINES (data_figures field) — CRITICAL FOR QUALITY:
- Generate 2-5 data figures using matplotlib/seaborn from actual experiment data
- USE REAL DATA VALUES from the data analysis — do NOT use placeholder values
- Supported types: bar, barh, line, scatter, heatmap, pie, box, violin, confusion_matrix, roc_curve, multi_panel
- For model comparisons: bar chart with actual metric values
- For trends over time/epochs: line chart with actual data points
- For correlations: scatter plot with actual x,y values
- For distributions: violin or box plot
- For multi-metric comparison: multi_panel with subplots
- Each figure must have: type, data (with actual values), title, xlabel, ylabel, caption (bilingual), label
- Use descriptive fig IDs like "fig_accuracy_bar", "fig_loss_curve", "fig_correlation"
- Reference figures in section "figures" arrays

DATA FORMAT EXAMPLES BY TYPE:
- bar:     {"labels": [...], "values": [...]} or grouped: {"labels": [...], "values": [[...],[...]], "group_labels": [...]}
- line:    {"x": [...], "y": [...]} or multi: {"x": [...], "y": [[...],[...]], "labels": [...]}
- scatter: {"x": [...], "y": [...]} or with groups: {"x": [...], "y": [...], "hue": [...], "hue_labels": {"0": "A"}}
- heatmap: {"matrix": [[...]], "xlabels": [...], "ylabels": [...]}
- box/violin: {"groups": {"Group A": [...], "Group B": [...]}}
- multi_panel: {"panels": [<sub-specs>], "layout": [nrows, ncols]}

DIAGRAM GUIDELINES (diagrams field):
- Generate 1-2 conceptual diagrams using Mermaid.js syntax (method pipelines, architectures)
- Good types: flowcharts (graph TD/LR), sequence diagrams
- Use short labels (max 4-5 words per node)
- Each diagram needs: mermaid (syntax), caption (bilingual), label

SECTION GUIDELINES:
- Abstract: 150-250 words, summarize objective/methods/results/conclusion
- Introduction: 500-800 words, background/motivation/objective
- Methods: 400-700 words, detailed methodology, subsections recommended
- Results: 500-800 words, present findings with references to data figures and tables
- Discussion: 400-700 words, interpret results, limitations, implications
- Conclusion: 200-300 words, summarize and future work
"""

_USER_PROMPT_TEMPLATE = """\
Generate a complete academic paper draft based on the following information.

## Paper Title
English: {title_en}
Japanese: {title_ja}

## Research Overview
{overview}

## Data Analysis Results
```json
{data_analysis}
```
{extra_context}
## Instructions
1. Generate all standard sections: Abstract, Introduction, Methods, Results, Discussion, Conclusion
2. If the data analysis suggests specific findings, incorporate them into Results and Discussion
3. Suggest appropriate tables based on the data (include actual values from the analysis)
4. Suggest 3-5 relevant references (use plausible but clearly marked as suggested)
5. Write both English and Japanese for every text field
6. Generate 1-3 diagrams in Mermaid.js syntax (method pipeline, architecture, comparison, etc.)
7. Reference diagrams in sections via the "figures" array
8. Return ONLY valid JSON matching the schema described in your instructions
"""


# ---------------------------------------------------------------------------
# Default Azure OpenAI settings
# ---------------------------------------------------------------------------

_DEFAULT_AZURE_ENDPOINT = "https://gpt5-genome-eastus2.openai.azure.com/"
_DEFAULT_DEPLOYMENT = "gpt-5.2"
_DEFAULT_API_VERSION = "2025-01-01-preview"


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

def get_backend() -> str:
    """Get the configured backend: 'claude' or 'azure'."""
    backend = os.environ.get("PAPERFORGE_BACKEND", "claude").lower()
    if backend not in ("claude", "azure"):
        backend = "claude"
    return backend


# ---------------------------------------------------------------------------
# Claude Code Backend
# ---------------------------------------------------------------------------

class ClaudeCodeBackend:
    """Uses Claude Code CLI (`claude -p`) as the AI backend."""

    def __init__(self):
        # Check if claude command is available
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise TextGenerationError("Claude Code CLI not found or not working")
        except FileNotFoundError:
            raise TextGenerationError(
                "Claude Code CLI not found. Install it with: npm install -g @anthropic-ai/claude-code"
            )

    def call(self, system: str, user: str, max_retries: int = 2) -> str:
        """Call Claude Code CLI with the given prompts."""
        # Combine system and user prompts
        full_prompt = f"""{system}

---

{user}"""

        last_error = None
        for attempt in range(max_retries):
            try:
                # Use claude -p with minimal options for reliability
                # --tools "" disables tool use to get pure text output
                result = subprocess.run(
                    [
                        "claude", "-p", full_prompt,
                        "--output-format", "text",
                        "--tools", "",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600,  # 10 minute timeout for long generation
                    env={**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"},
                )

                if result.returncode != 0:
                    stderr = result.stderr.strip()
                    if stderr:
                        raise TextGenerationError(f"Claude Code error: {stderr}")
                    # Sometimes returncode is non-zero but output is fine
                    if not result.stdout.strip():
                        raise TextGenerationError("Claude Code returned no output")

                output = result.stdout.strip()
                if not output:
                    raise TextGenerationError("Claude Code returned empty response")

                return output

            except subprocess.TimeoutExpired:
                last_error = "Claude Code timed out after 10 minutes"
                if attempt < max_retries - 1:
                    time.sleep(2)
            except TextGenerationError:
                raise
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(2)

        raise TextGenerationError(
            f"Claude Code call failed after {max_retries} attempts: {last_error}"
        )


# ---------------------------------------------------------------------------
# Azure OpenAI Backend
# ---------------------------------------------------------------------------

class AzureOpenAIBackend:
    """Uses Azure OpenAI API as the AI backend."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ):
        if AzureOpenAI is None:
            raise ImportError(
                "The 'openai' package is required for Azure backend. "
                "Install it with: pip install openai"
            )

        resolved_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY", "")
        if not resolved_key:
            raise ValueError(
                "Azure OpenAI API key is required. "
                "Set AZURE_OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self.endpoint = endpoint or os.environ.get(
            "AZURE_OPENAI_ENDPOINT", _DEFAULT_AZURE_ENDPOINT
        )
        self.deployment = deployment or os.environ.get(
            "AZURE_OPENAI_DEPLOYMENT", _DEFAULT_DEPLOYMENT
        )
        self.api_version = api_version or _DEFAULT_API_VERSION

        self.client = AzureOpenAI(
            api_key=resolved_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )

    def call(self, system: str, user: str, max_retries: int = 3) -> str:
        """Call Azure OpenAI API with retry logic."""
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    max_completion_tokens=16384,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                content = response.choices[0].message.content
                if content is None:
                    raise TextGenerationError("API returned empty response")
                return content
            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                if "rate" in err_str or "429" in err_str or "throttl" in err_str:
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                elif attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    break

        raise TextGenerationError(
            f"Azure OpenAI API call failed after {max_retries} attempts: {last_error}"
        )


# ---------------------------------------------------------------------------
# TextGenerator (unified interface)
# ---------------------------------------------------------------------------

class TextGenerator:
    """Generates academic paper content using AI.

    Supports multiple backends:
    - Claude Code CLI (default): No API key needed, uses `claude -p`
    - Azure OpenAI: Set PAPERFORGE_BACKEND=azure and configure API keys

    The backend can be selected via:
    - Environment variable: PAPERFORGE_BACKEND=claude or PAPERFORGE_BACKEND=azure
    - Constructor parameter: backend="claude" or backend="azure"
    """

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
        backend: str | None = None,
    ):
        """Initialize TextGenerator with specified backend.

        Args:
            api_key: Azure OpenAI API key (only for azure backend)
            endpoint: Azure OpenAI endpoint URL (only for azure backend)
            deployment: Azure OpenAI deployment name (only for azure backend)
            api_version: Azure OpenAI API version (only for azure backend)
            backend: "claude" or "azure". If None, uses PAPERFORGE_BACKEND env var.
        """
        self.backend_name = backend or get_backend()

        if self.backend_name == "azure":
            self._backend = AzureOpenAIBackend(
                api_key=api_key,
                endpoint=endpoint,
                deployment=deployment,
                api_version=api_version,
            )
        else:
            self._backend = ClaudeCodeBackend()

    def generate_paper(
        self,
        overview: str,
        data_analysis: dict | None = None,
        title_en: str = "Untitled Paper",
        title_ja: str = "無題の論文",
        authors: list[dict] | None = None,
        template: str = "twocol",
        extra_context: str = "",
    ) -> tuple[PaperSpec, dict]:
        """Generate a complete paper spec from overview and data.

        Args:
            overview: Natural language description of the research.
            data_analysis: Structured data analysis results (from Pipeline.analyze_data).
            title_en: Paper title in English.
            title_ja: Paper title in Japanese.
            authors: List of author dicts with name/affiliation/email.
            template: LaTeX template name.
            extra_context: Additional context (experiment structure, document text, etc.).

        Returns:
            Tuple of (PaperSpec, generation_extras).
            generation_extras is a dict with "diagrams" and "data_figures" keys.
        """
        # Build extra context block
        extra_block = ""
        if extra_context:
            extra_block = f"\n## Additional Context (Experiment Data & Documents)\n{extra_context}\n"

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            title_en=title_en,
            title_ja=title_ja,
            overview=overview,
            data_analysis=json.dumps(data_analysis or {}, indent=2, ensure_ascii=False),
            extra_context=extra_block,
        )

        response_text = self._backend.call(_SYSTEM_PROMPT, user_prompt)
        spec, extras = self._parse_response(
            response_text,
            title_en=title_en,
            title_ja=title_ja,
            authors=authors,
            template=template,
        )
        return spec, extras

    def _parse_response(
        self,
        response_text: str,
        title_en: str,
        title_ja: str,
        authors: list[dict] | None,
        template: str,
    ) -> tuple[PaperSpec, dict]:
        """Parse the JSON response into a PaperSpec and diagrams dict."""
        # Strip markdown code fences if present
        cleaned = response_text.strip()
        json_match = re.search(r"```(?:json)?\s*\n(.*?)```", cleaned, re.DOTALL)
        if json_match:
            cleaned = json_match.group(1).strip()

        # Try to find JSON object in the response
        if not cleaned.startswith("{"):
            # Look for first { and last }
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                cleaned = cleaned[start:end+1]

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise TextGenerationError(
                f"Failed to parse AI response as JSON: {e}\n"
                f"Raw response (first 500 chars): {response_text[:500]}"
            )

        # Build PaperSpec from parsed data
        sections = []
        for sec in data.get("sections", []):
            subsections = []
            for sub in sec.get("subsections", []):
                subsections.append(Section(
                    heading=BilingualText.from_value(sub.get("heading", {})),
                    content=BilingualText.from_value(sub.get("content", {})),
                ))
            sections.append(Section(
                heading=BilingualText.from_value(sec.get("heading", {})),
                content=BilingualText.from_value(sec.get("content", {})),
                figures=sec.get("figures", []),
                tables=sec.get("tables", []),
                subsections=subsections,
            ))

        # Tables
        tables = {}
        for tab_id, tab_data in data.get("tables", {}).items():
            tables[tab_id] = TableSpec(
                caption=BilingualText.from_value(tab_data.get("caption", {})),
                label=tab_data.get("label", f"tab:{tab_id}"),
                columns=tab_data.get("columns", []),
                data=tab_data.get("data", []),
            )

        # References
        references = []
        for ref in data.get("references", []):
            if isinstance(ref, str):
                references.append(Reference(key="", authors="", title=ref))
            elif isinstance(ref, dict):
                references.append(Reference(
                    key=ref.get("key", ""),
                    authors=ref.get("authors", ""),
                    title=ref.get("title", ""),
                    journal=ref.get("journal", ""),
                    year=ref.get("year", 0),
                    doi=ref.get("doi", ""),
                ))

        # Authors
        author_list = []
        if authors:
            for a in authors:
                if isinstance(a, str):
                    author_list.append(Author(name=a))
                elif isinstance(a, dict):
                    author_list.append(Author(**{
                        k: v for k, v in a.items()
                        if k in ("name", "affiliation", "email")
                    }))

        # Diagrams (Mermaid) and data figures (matplotlib)
        diagrams = data.get("diagrams", {})
        data_figures = data.get("data_figures", {})

        # Build FigureSpec entries for all figures
        figures = {}
        for fig_id, diag in diagrams.items():
            figures[fig_id] = FigureSpec(
                path=f"figures/{fig_id}.png",
                caption=BilingualText.from_value(diag.get("caption", {})),
                label=diag.get("label", f"fig:{fig_id}"),
                wide=diag.get("wide", False),
            )
        for fig_id, dfig in data_figures.items():
            figures[fig_id] = FigureSpec(
                path=f"figures/{fig_id}.png",
                caption=BilingualText.from_value(dfig.get("caption", {})),
                label=dfig.get("label", f"fig:{fig_id}"),
                wide=dfig.get("wide", False),
            )

        spec = PaperSpec(
            meta={
                "title": {"en": title_en, "ja": title_ja},
                "template": template,
                "date": "",
            },
            authors=author_list,
            keywords=BilingualText.from_value(data.get("keywords", {})),
            abstract=BilingualText.from_value(data.get("abstract", {})),
            sections=sections,
            figures=figures,
            tables=tables,
            references=references,
            acknowledgments=BilingualText.from_value(data.get("acknowledgments", {})),
        )

        extras = {"diagrams": diagrams, "data_figures": data_figures}
        return spec, extras
