"""Citation Hallucination Checker using multiple APIs.

Verifies that references in the paper actually exist and have correct metadata.
Uses CrossRef (primary), Semantic Scholar, and OpenAlex as fallback sources.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

# API endpoints
CROSSREF_API = "https://api.crossref.org/works"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"
OPENALEX_API = "https://api.openalex.org"

# Cache directory
CACHE_DIR = Path.home() / ".cache" / "paperclaw" / "citations"


@dataclass
class VerificationResult:
    """Result of verifying a single reference."""
    key: str
    title: str
    status: str  # "verified", "not_found", "mismatch", "error"
    confidence: float  # 0.0 - 1.0
    message: str
    source: str = ""  # "crossref", "semantic_scholar", "openalex"
    suggested_correction: dict | None = None
    doi: str | None = None
    url: str | None = None


@dataclass
class CheckerReport:
    """Complete report from citation checker."""
    total_references: int
    verified: int
    not_found: int
    mismatched: int
    errors: int
    results: list[VerificationResult]
    sources_used: dict[str, int] = field(default_factory=dict)

    @property
    def verification_rate(self) -> float:
        if self.total_references == 0:
            return 1.0
        return self.verified / self.total_references

    def to_dict(self) -> dict:
        return {
            "total_references": self.total_references,
            "verified": self.verified,
            "not_found": self.not_found,
            "mismatched": self.mismatched,
            "errors": self.errors,
            "verification_rate": self.verification_rate,
            "sources_used": self.sources_used,
            "results": [
                {
                    "key": r.key,
                    "title": r.title,
                    "status": r.status,
                    "confidence": r.confidence,
                    "message": r.message,
                    "source": r.source,
                    "doi": r.doi,
                    "url": r.url,
                    "suggested_correction": r.suggested_correction,
                }
                for r in self.results
            ],
        }


class CitationChecker:
    """Checks references for hallucinations using multiple academic APIs.

    Features:
    - CrossRef API (primary) - best for DOI lookup and metadata
    - Semantic Scholar API (fallback) - good for CS/AI papers
    - OpenAlex API (fallback) - broad coverage, no rate limits
    - Local caching to reduce API calls
    - Automatic retry with exponential backoff

    Usage:
        checker = CitationChecker()
        report = checker.check_references(paper_spec)
        print(f"Verified: {report.verified}/{report.total_references}")
    """

    def __init__(
        self,
        semantic_scholar_api_key: str | None = None,
        use_cache: bool = True,
        cache_ttl_days: int = 7,
        max_retries: int = 3,
    ):
        """Initialize citation checker.

        Args:
            semantic_scholar_api_key: API key for higher rate limits
            use_cache: Whether to cache API responses
            cache_ttl_days: Cache time-to-live in days
            max_retries: Maximum retry attempts for failed requests
        """
        self.semantic_scholar_api_key = semantic_scholar_api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.use_cache = use_cache
        self.cache_ttl_days = cache_ttl_days
        self.max_retries = max_retries

        if self.use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, query: str, source: str) -> str:
        """Generate cache key for a query."""
        content = f"{source}:{query}".encode()
        return hashlib.md5(content).hexdigest()

    def _get_cached(self, cache_key: str) -> dict | None:
        """Get cached response if valid."""
        if not self.use_cache:
            return None

        cache_file = CACHE_DIR / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text())
            cached_time = data.get("_cached_at", 0)
            if time.time() - cached_time > self.cache_ttl_days * 86400:
                cache_file.unlink()
                return None
            return data.get("response")
        except Exception:
            return None

    def _set_cached(self, cache_key: str, response: dict) -> None:
        """Cache a response."""
        if not self.use_cache:
            return

        cache_file = CACHE_DIR / f"{cache_key}.json"
        try:
            data = {"_cached_at": time.time(), "response": response}
            cache_file.write_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.debug(f"Cache write failed: {e}")

    def _api_request(
        self,
        url: str,
        headers: dict | None = None,
        timeout: int = 30,
    ) -> dict | None:
        """Make an API request with retry logic."""
        headers = headers or {}
        headers.setdefault("User-Agent", "PaperClaw/1.0 (mailto:paperclaw@example.com)")

        for attempt in range(self.max_retries):
            try:
                req = Request(url, headers=headers)
                with urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as e:
                if e.code == 404:
                    return None
                elif e.code == 429:
                    wait_time = (2 ** attempt) * 2
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"HTTP error {e.code}: {e.reason}")
                    if attempt == self.max_retries - 1:
                        return None
            except URLError as e:
                logger.error(f"URL error: {e.reason}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)
            except Exception as e:
                logger.error(f"Request failed: {e}")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(1)

        return None

    def _search_crossref(self, title: str, authors: str = "", year: int = 0) -> list[dict]:
        """Search CrossRef for papers."""
        cache_key = self._get_cache_key(f"{title}:{authors}:{year}", "crossref")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build query
        query_parts = [title]
        if authors:
            first_author = authors.split(",")[0].strip()
            query_parts.append(first_author)

        params = {
            "query": " ".join(query_parts),
            "rows": 5,
            "select": "DOI,title,author,published-print,published-online,container-title,type",
        }

        if year:
            params["filter"] = f"from-pub-date:{year-1},until-pub-date:{year+1}"

        url = f"{CROSSREF_API}?{urlencode(params)}"
        result = self._api_request(url)

        papers = []
        if result and "message" in result and "items" in result["message"]:
            for item in result["message"]["items"]:
                paper = {
                    "title": item.get("title", [""])[0] if item.get("title") else "",
                    "doi": item.get("DOI", ""),
                    "year": None,
                    "authors": [],
                    "venue": item.get("container-title", [""])[0] if item.get("container-title") else "",
                    "source": "crossref",
                }

                # Extract year
                if item.get("published-print"):
                    paper["year"] = item["published-print"].get("date-parts", [[None]])[0][0]
                elif item.get("published-online"):
                    paper["year"] = item["published-online"].get("date-parts", [[None]])[0][0]

                # Extract authors
                if item.get("author"):
                    paper["authors"] = [
                        f"{a.get('given', '')} {a.get('family', '')}".strip()
                        for a in item["author"]
                    ]

                papers.append(paper)

        self._set_cached(cache_key, papers)
        time.sleep(0.5)  # Polite delay for CrossRef
        return papers

    def _search_semantic_scholar(self, title: str, authors: str = "") -> list[dict]:
        """Search Semantic Scholar for papers."""
        cache_key = self._get_cache_key(f"{title}:{authors}", "s2")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        clean_title = re.sub(r'[^\w\s]', ' ', title).strip()
        params = {
            "query": clean_title,
            "limit": 5,
            "fields": "title,authors,year,venue,externalIds,citationCount,url",
        }

        url = f"{SEMANTIC_SCHOLAR_API}/paper/search?{urlencode(params)}"
        headers = {"Accept": "application/json"}
        if self.semantic_scholar_api_key:
            headers["x-api-key"] = self.semantic_scholar_api_key

        result = self._api_request(url, headers)

        papers = []
        if result and "data" in result:
            for item in result["data"]:
                external_ids = item.get("externalIds") or {}
                paper = {
                    "title": item.get("title", ""),
                    "doi": external_ids.get("DOI", ""),
                    "year": item.get("year"),
                    "authors": [a.get("name", "") for a in item.get("authors", [])],
                    "venue": item.get("venue", ""),
                    "citation_count": item.get("citationCount", 0),
                    "source": "semantic_scholar",
                    "url": item.get("url", ""),
                }
                papers.append(paper)

        self._set_cached(cache_key, papers)
        time.sleep(1.0)  # Semantic Scholar rate limit
        return papers

    def _search_openalex(self, title: str, authors: str = "") -> list[dict]:
        """Search OpenAlex for papers (no rate limits)."""
        cache_key = self._get_cache_key(f"{title}:{authors}", "openalex")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # OpenAlex uses different search format
        search_query = title.replace(" ", "+")
        params = {
            "search": search_query,
            "per_page": 5,
            "select": "id,doi,title,authorships,publication_year,primary_location",
        }

        url = f"{OPENALEX_API}/works?{urlencode(params)}"
        result = self._api_request(url)

        papers = []
        if result and "results" in result:
            for item in result["results"]:
                paper = {
                    "title": item.get("title", ""),
                    "doi": (item.get("doi") or "").replace("https://doi.org/", ""),
                    "year": item.get("publication_year"),
                    "authors": [],
                    "venue": "",
                    "source": "openalex",
                    "url": item.get("id", ""),
                }

                # Extract authors
                if item.get("authorships"):
                    paper["authors"] = [
                        a.get("author", {}).get("display_name", "")
                        for a in item["authorships"]
                    ]

                # Extract venue
                if item.get("primary_location") and item["primary_location"].get("source"):
                    paper["venue"] = item["primary_location"]["source"].get("display_name", "")

                papers.append(paper)

        self._set_cached(cache_key, papers)
        time.sleep(0.2)  # Light delay for OpenAlex
        return papers

    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles using Jaccard index."""
        def normalize(t: str) -> set[str]:
            # Remove punctuation, lowercase, split into words
            words = set(re.sub(r'[^\w\s]', '', t.lower()).split())
            # Remove common stop words
            stop_words = {'a', 'an', 'the', 'of', 'in', 'on', 'for', 'to', 'and', 'or', 'with'}
            return words - stop_words

        words1 = normalize(title1)
        words2 = normalize(title2)

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _verify_by_doi(self, doi: str) -> dict | None:
        """Verify a paper exists by DOI (most reliable)."""
        if not doi:
            return None

        # Clean DOI
        doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")

        cache_key = self._get_cache_key(doi, "doi")
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{CROSSREF_API}/{quote_plus(doi)}"
        result = self._api_request(url)

        if result and "message" in result:
            item = result["message"]
            paper = {
                "title": item.get("title", [""])[0] if item.get("title") else "",
                "doi": item.get("DOI", ""),
                "year": None,
                "authors": [],
                "venue": item.get("container-title", [""])[0] if item.get("container-title") else "",
                "source": "crossref",
            }

            if item.get("published-print"):
                paper["year"] = item["published-print"].get("date-parts", [[None]])[0][0]

            if item.get("author"):
                paper["authors"] = [
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in item["author"]
                ]

            self._set_cached(cache_key, paper)
            return paper

        return None

    def _verify_reference(self, ref: dict) -> VerificationResult:
        """Verify a single reference using multiple sources."""
        key = ref.get("key", "unknown")
        title = ref.get("title", "")
        authors = ref.get("authors", "")
        year = ref.get("year", 0)
        doi = ref.get("doi", "")

        if not title and not doi:
            return VerificationResult(
                key=key,
                title=title,
                status="error",
                confidence=0.0,
                message="Reference has no title or DOI",
            )

        # Strategy 1: If DOI provided, verify directly (highest confidence)
        if doi:
            paper = self._verify_by_doi(doi)
            if paper:
                return VerificationResult(
                    key=key,
                    title=title,
                    status="verified",
                    confidence=1.0,
                    message=f"DOI verified: {doi}",
                    source="crossref",
                    doi=doi,
                    url=f"https://doi.org/{doi}",
                )

        # Strategy 2: Search multiple APIs and find best match
        all_papers = []

        # Try CrossRef first (best metadata)
        crossref_results = self._search_crossref(title, authors, year)
        all_papers.extend(crossref_results)

        # If no good match, try Semantic Scholar
        if not any(self._calculate_similarity(title, p["title"]) > 0.7 for p in all_papers):
            s2_results = self._search_semantic_scholar(title, authors)
            all_papers.extend(s2_results)

        # If still no good match, try OpenAlex
        if not any(self._calculate_similarity(title, p["title"]) > 0.7 for p in all_papers):
            openalex_results = self._search_openalex(title, authors)
            all_papers.extend(openalex_results)

        if not all_papers:
            return VerificationResult(
                key=key,
                title=title,
                status="not_found",
                confidence=0.0,
                message=f"Paper not found in any database: '{title[:60]}...'",
            )

        # Find best match
        best_match = None
        best_score = 0.0

        for paper in all_papers:
            paper_title = paper.get("title", "")
            score = self._calculate_similarity(title, paper_title)

            # Bonus for year match
            if year and paper.get("year") == year:
                score += 0.15

            # Bonus for author match
            if authors and paper.get("authors"):
                first_author_ref = authors.split(",")[0].split()[-1].lower() if authors else ""
                first_author_paper = paper["authors"][0].split()[-1].lower() if paper["authors"] else ""
                if first_author_ref and first_author_paper:
                    if first_author_ref == first_author_paper:
                        score += 0.2
                    elif first_author_ref in first_author_paper or first_author_paper in first_author_ref:
                        score += 0.1

            if score > best_score:
                best_score = score
                best_match = paper

        if best_match and best_score >= 0.75:
            return VerificationResult(
                key=key,
                title=title,
                status="verified",
                confidence=min(best_score, 1.0),
                message=f"Verified via {best_match['source']}: '{best_match['title'][:50]}...'",
                source=best_match["source"],
                doi=best_match.get("doi"),
                url=best_match.get("url") or (f"https://doi.org/{best_match['doi']}" if best_match.get("doi") else None),
            )
        elif best_match and best_score >= 0.4:
            return VerificationResult(
                key=key,
                title=title,
                status="mismatch",
                confidence=best_score,
                message=f"Possible mismatch. Did you mean: '{best_match['title'][:50]}...'?",
                source=best_match["source"],
                suggested_correction={
                    "title": best_match["title"],
                    "authors": ", ".join(best_match.get("authors", [])[:3]),
                    "year": best_match.get("year"),
                    "doi": best_match.get("doi"),
                    "venue": best_match.get("venue"),
                },
            )
        else:
            return VerificationResult(
                key=key,
                title=title,
                status="not_found",
                confidence=0.0,
                message=f"No matching paper found: '{title[:60]}...'",
            )

    def check_references(self, paper_spec: dict) -> CheckerReport:
        """Check all references in a paper specification.

        Args:
            paper_spec: Paper specification dict with "references" key

        Returns:
            CheckerReport with verification results
        """
        references = paper_spec.get("references", [])
        results = []
        sources_used: dict[str, int] = {}

        verified = 0
        not_found = 0
        mismatched = 0
        errors = 0

        for ref in references:
            if isinstance(ref, str):
                ref = {"title": ref, "key": ""}

            result = self._verify_reference(ref)
            results.append(result)

            if result.source:
                sources_used[result.source] = sources_used.get(result.source, 0) + 1

            if result.status == "verified":
                verified += 1
                logger.info(f"[VERIFIED] {result.title[:50]}... ({result.source})")
            elif result.status == "not_found":
                not_found += 1
                logger.warning(f"[NOT FOUND] {result.title[:50]}...")
            elif result.status == "mismatch":
                mismatched += 1
                logger.warning(f"[MISMATCH] {result.title[:50]}...")
            else:
                errors += 1
                logger.error(f"[ERROR] {result.title[:50]}...")

        return CheckerReport(
            total_references=len(references),
            verified=verified,
            not_found=not_found,
            mismatched=mismatched,
            errors=errors,
            results=results,
            sources_used=sources_used,
        )

    def check_and_fix(self, paper_spec: dict) -> tuple[CheckerReport, dict]:
        """Check references and return corrected paper_spec.

        Args:
            paper_spec: Paper specification dict

        Returns:
            Tuple of (CheckerReport, corrected_paper_spec)
        """
        report = self.check_references(paper_spec)

        corrected_refs = []
        references = paper_spec.get("references", [])

        for i, result in enumerate(report.results):
            if result.status == "verified":
                ref = references[i] if i < len(references) else {"key": result.key}
                if isinstance(ref, dict) and result.doi and not ref.get("doi"):
                    ref = ref.copy()
                    ref["doi"] = result.doi
                corrected_refs.append(ref)
            elif result.status == "mismatch" and result.suggested_correction:
                corrected = result.suggested_correction.copy()
                corrected["key"] = result.key
                corrected_refs.append(corrected)
            else:
                ref = references[i] if i < len(references) else {"key": result.key, "title": result.title}
                if isinstance(ref, dict):
                    ref = ref.copy()
                    ref["_unverified"] = True
                corrected_refs.append(ref)

        corrected_spec = paper_spec.copy()
        corrected_spec["references"] = corrected_refs

        return report, corrected_spec
