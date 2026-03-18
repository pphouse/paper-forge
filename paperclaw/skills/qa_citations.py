"""QA Citations Skill - Verify citations against external APIs."""

from __future__ import annotations

from pathlib import Path
import time
import json
import hashlib
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

from .base import Skill, SkillResult, SkillContext, SkillStatus
from .registry import register_skill


@dataclass
class CitationResult:
    """Result of citation verification."""
    key: str
    title: str
    status: str  # "verified", "mismatch", "not_found", "error"
    confidence: float
    source: str  # API that verified
    suggested_doi: Optional[str] = None
    message: str = ""


@register_skill
class QaCitationsSkill(Skill):
    """Verify citations against external academic databases.

    Input:
        - Paper specification with references

    Output:
        - Verification results for each citation
        - Suggested corrections
    """

    @property
    def name(self) -> str:
        return "qa-citations"

    @property
    def description(self) -> str:
        return "Verify citations using CrossRef and OpenAlex APIs"

    def execute(self, context: SkillContext) -> SkillResult:
        result = SkillResult(status=SkillStatus.SUCCESS)

        references = context.spec.get("references", [])
        if not references:
            result.add_message("No references to verify")
            return result

        # Setup cache
        cache_dir = context.cache_dir / "citations"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Verify each reference
        verified = 0
        not_found = 0
        mismatched = 0
        citation_results = []

        for ref in references:
            if not isinstance(ref, dict):
                continue

            cit_result = self._verify_citation(ref, cache_dir)
            citation_results.append(cit_result)

            if cit_result.status == "verified":
                verified += 1
            elif cit_result.status == "not_found":
                not_found += 1
                result.add_message(f"[NOT FOUND] {cit_result.title[:50]}...")
            elif cit_result.status == "mismatch":
                mismatched += 1
                result.add_message(f"[MISMATCH] {cit_result.title[:50]}...")

        # Summary
        total = len(references)
        result.data["citations"] = [vars(c) for c in citation_results]
        result.data["summary"] = {
            "total": total,
            "verified": verified,
            "not_found": not_found,
            "mismatched": mismatched,
        }

        result.metrics["total_references"] = total
        result.metrics["verified"] = verified
        result.metrics["verification_rate"] = round(verified / total * 100, 1) if total > 0 else 0

        if not_found > 0 or mismatched > 0:
            result.status = SkillStatus.WARNING
            result.add_message(f"Verified: {verified}/{total} ({result.metrics['verification_rate']}%)")
        else:
            result.add_message(f"All {total} citations verified")

        return result

    def _verify_citation(self, ref: dict, cache_dir: Path) -> CitationResult:
        """Verify a single citation."""
        title = ref.get("title", "")
        key = ref.get("key", "")
        authors = ref.get("authors", "")

        # Check cache
        cache_key = hashlib.md5(f"{title}:{authors}".encode()).hexdigest()
        cache_file = cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text())
                # Check TTL (24 hours)
                if time.time() - cached.get("timestamp", 0) < 86400:
                    return CitationResult(**cached["result"])
            except Exception:
                pass

        # Try CrossRef
        result = self._check_crossref(title, authors)

        if result.status != "verified":
            # Fallback to OpenAlex
            result = self._check_openalex(title, authors)

        # Cache result
        try:
            cache_file.write_text(json.dumps({
                "timestamp": time.time(),
                "result": vars(result),
            }))
        except Exception:
            pass

        return result

    def _check_crossref(self, title: str, authors: str) -> CitationResult:
        """Check citation against CrossRef API."""
        try:
            query = urllib.parse.quote(title)
            url = f"https://api.crossref.org/works?query.title={query}&rows=1"

            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={
                        "User-Agent": "PaperClaw/1.0 (mailto:paperclaw@example.com)"
                    })
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode())
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:  # Rate limited
                        time.sleep(2 ** attempt)
                        continue
                    raise
            else:
                return CitationResult(
                    key="", title=title, status="error",
                    confidence=0, source="crossref",
                    message="Rate limited"
                )

            items = data.get("message", {}).get("items", [])
            if not items:
                return CitationResult(
                    key="", title=title, status="not_found",
                    confidence=0, source="crossref"
                )

            item = items[0]
            found_title = item.get("title", [""])[0]

            # Calculate similarity
            similarity = self._title_similarity(title, found_title)

            if similarity > 0.8:
                return CitationResult(
                    key="", title=title, status="verified",
                    confidence=similarity, source="crossref",
                    suggested_doi=item.get("DOI")
                )
            else:
                return CitationResult(
                    key="", title=title, status="mismatch",
                    confidence=similarity, source="crossref",
                    message=f"Found: {found_title[:50]}..."
                )

        except Exception as e:
            return CitationResult(
                key="", title=title, status="error",
                confidence=0, source="crossref",
                message=str(e)
            )

    def _check_openalex(self, title: str, authors: str) -> CitationResult:
        """Check citation against OpenAlex API."""
        try:
            query = urllib.parse.quote(title)
            url = f"https://api.openalex.org/works?filter=title.search:{query}&per_page=1"

            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={
                        "User-Agent": "PaperClaw/1.0"
                    })
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode())
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429:
                        time.sleep(2 ** attempt)
                        continue
                    raise
            else:
                return CitationResult(
                    key="", title=title, status="error",
                    confidence=0, source="openalex",
                    message="Rate limited"
                )

            results = data.get("results", [])
            if not results:
                return CitationResult(
                    key="", title=title, status="not_found",
                    confidence=0, source="openalex"
                )

            item = results[0]
            found_title = item.get("title", "")
            similarity = self._title_similarity(title, found_title)

            if similarity > 0.8:
                return CitationResult(
                    key="", title=title, status="verified",
                    confidence=similarity, source="openalex",
                    suggested_doi=item.get("doi")
                )
            else:
                return CitationResult(
                    key="", title=title, status="mismatch",
                    confidence=similarity, source="openalex",
                    message=f"Found: {found_title[:50]}..."
                )

        except Exception as e:
            return CitationResult(
                key="", title=title, status="error",
                confidence=0, source="openalex",
                message=str(e)
            )

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity using token overlap."""
        def normalize(s):
            return set(s.lower().split())

        t1 = normalize(title1)
        t2 = normalize(title2)

        if not t1 or not t2:
            return 0.0

        intersection = len(t1 & t2)
        union = len(t1 | t2)

        return intersection / union if union > 0 else 0.0
