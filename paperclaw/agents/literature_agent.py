"""Literature Research Agent for finding related papers.

Searches arxiv, biorxiv, and Semantic Scholar for relevant literature.
"""

from __future__ import annotations

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus, urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
BIORXIV_API = "https://api.biorxiv.org/details/biorxiv"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


@dataclass
class Paper:
    """Represents a research paper."""
    title: str
    authors: list[str]
    abstract: str
    year: int
    source: str  # "arxiv", "biorxiv", "semantic_scholar"
    url: str
    doi: str = ""
    arxiv_id: str = ""
    citation_count: int = 0
    relevance_score: float = 0.0
    categories: list[str] = field(default_factory=list)

    def to_reference(self) -> dict:
        """Convert to paper_spec reference format."""
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."

        return {
            "key": self._generate_key(),
            "authors": authors_str,
            "title": self.title,
            "journal": self.source.replace("_", " ").title(),
            "year": self.year,
            "doi": self.doi,
        }

    def _generate_key(self) -> str:
        """Generate a citation key."""
        if self.authors:
            first_author = self.authors[0].split()[-1].lower()
            return f"{first_author}{self.year}"
        return f"paper{self.year}"


@dataclass
class LiteratureReport:
    """Report from literature search."""
    query: str
    total_found: int
    papers: list[Paper]
    sources_searched: list[str]

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "total_found": self.total_found,
            "sources_searched": self.sources_searched,
            "papers": [
                {
                    "title": p.title,
                    "authors": p.authors,
                    "year": p.year,
                    "source": p.source,
                    "url": p.url,
                    "citation_count": p.citation_count,
                    "relevance_score": p.relevance_score,
                }
                for p in self.papers
            ],
        }

    def get_suggested_references(self, max_refs: int = 10) -> list[dict]:
        """Get top papers as references."""
        sorted_papers = sorted(
            self.papers,
            key=lambda p: (p.relevance_score, p.citation_count),
            reverse=True,
        )
        return [p.to_reference() for p in sorted_papers[:max_refs]]


class LiteratureAgent:
    """Agent for searching and recommending related literature.

    Usage:
        agent = LiteratureAgent()
        report = agent.search("attention mechanism medical imaging")
        references = report.get_suggested_references(5)
    """

    def __init__(self, rate_limit_delay: float = 1.0):
        """Initialize literature agent.

        Args:
            rate_limit_delay: Seconds to wait between API calls
        """
        self.rate_limit_delay = rate_limit_delay

    def _search_arxiv(self, query: str, max_results: int = 20) -> list[Paper]:
        """Search arxiv for papers."""
        papers = []

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        url = f"{ARXIV_API}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=30) as response:
                xml_data = response.read().decode("utf-8")

            # Parse XML
            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                title_text = title.text.strip().replace("\n", " ") if title is not None else ""

                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text)

                abstract = entry.find("atom:summary", ns)
                abstract_text = abstract.text.strip().replace("\n", " ") if abstract is not None else ""

                published = entry.find("atom:published", ns)
                year = int(published.text[:4]) if published is not None else 0

                arxiv_id = ""
                link = entry.find("atom:id", ns)
                if link is not None:
                    arxiv_id = link.text.split("/abs/")[-1]

                categories = []
                for cat in entry.findall("arxiv:primary_category", ns):
                    if cat.get("term"):
                        categories.append(cat.get("term"))

                papers.append(Paper(
                    title=title_text,
                    authors=authors,
                    abstract=abstract_text,
                    year=year,
                    source="arxiv",
                    url=f"https://arxiv.org/abs/{arxiv_id}",
                    arxiv_id=arxiv_id,
                    categories=categories,
                ))

        except Exception as e:
            logger.error(f"Arxiv search failed: {e}")

        time.sleep(self.rate_limit_delay)
        return papers

    def _search_biorxiv(self, query: str, max_results: int = 20) -> list[Paper]:
        """Search biorxiv for papers (last 30 days)."""
        papers = []

        # Biorxiv API is limited - search recent papers
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        url = f"{BIORXIV_API}/{start_date}/{end_date}/0/50"

        try:
            with urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            if "collection" in data:
                query_lower = query.lower()
                query_terms = set(query_lower.split())

                for item in data["collection"]:
                    title = item.get("title", "")
                    abstract = item.get("abstract", "")

                    # Simple relevance check
                    text_lower = (title + " " + abstract).lower()
                    matches = sum(1 for term in query_terms if term in text_lower)

                    if matches >= len(query_terms) * 0.3:  # At least 30% term match
                        authors = item.get("authors", "").split("; ")

                        papers.append(Paper(
                            title=title,
                            authors=authors,
                            abstract=abstract,
                            year=int(item.get("date", "2024")[:4]),
                            source="biorxiv",
                            url=f"https://www.biorxiv.org/content/{item.get('doi', '')}",
                            doi=item.get("doi", ""),
                            relevance_score=matches / len(query_terms),
                        ))

                        if len(papers) >= max_results:
                            break

        except Exception as e:
            logger.error(f"Biorxiv search failed: {e}")

        time.sleep(self.rate_limit_delay)
        return papers

    def _search_semantic_scholar(self, query: str, max_results: int = 20) -> list[Paper]:
        """Search Semantic Scholar for papers."""
        papers = []

        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,year,venue,externalIds,citationCount,url",
        }

        url = f"{SEMANTIC_SCHOLAR_API}/paper/search?{urlencode(params)}"

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            if "data" in data:
                for item in data["data"]:
                    authors = [a.get("name", "") for a in item.get("authors", [])]

                    external_ids = item.get("externalIds", {}) or {}
                    doi = external_ids.get("DOI", "")
                    arxiv_id = external_ids.get("ArXiv", "")

                    papers.append(Paper(
                        title=item.get("title", ""),
                        authors=authors,
                        abstract=item.get("abstract", "") or "",
                        year=item.get("year", 0) or 0,
                        source="semantic_scholar",
                        url=item.get("url", "") or f"https://www.semanticscholar.org/paper/{item.get('paperId', '')}",
                        doi=doi,
                        arxiv_id=arxiv_id,
                        citation_count=item.get("citationCount", 0) or 0,
                    ))

        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")

        time.sleep(self.rate_limit_delay)
        return papers

    def _calculate_relevance(self, paper: Paper, query_terms: set[str]) -> float:
        """Calculate relevance score for a paper."""
        text = (paper.title + " " + paper.abstract).lower()
        matches = sum(1 for term in query_terms if term in text)
        base_score = matches / len(query_terms) if query_terms else 0

        # Boost for citation count (log scale)
        import math
        citation_boost = math.log10(paper.citation_count + 1) * 0.05

        # Boost for recency
        from datetime import datetime
        current_year = datetime.now().year
        recency_boost = max(0, (paper.year - current_year + 5) * 0.02) if paper.year else 0

        return min(base_score + citation_boost + recency_boost, 1.0)

    def search(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results_per_source: int = 20,
    ) -> LiteratureReport:
        """Search for related literature.

        Args:
            query: Search query (keywords or natural language)
            sources: List of sources to search ("arxiv", "biorxiv", "semantic_scholar")
            max_results_per_source: Maximum results from each source

        Returns:
            LiteratureReport with found papers
        """
        if sources is None:
            sources = ["arxiv", "semantic_scholar"]

        all_papers = []
        searched_sources = []

        if "arxiv" in sources:
            logger.info("Searching arxiv...")
            papers = self._search_arxiv(query, max_results_per_source)
            all_papers.extend(papers)
            searched_sources.append("arxiv")
            logger.info(f"Found {len(papers)} papers on arxiv")

        if "biorxiv" in sources:
            logger.info("Searching biorxiv...")
            papers = self._search_biorxiv(query, max_results_per_source)
            all_papers.extend(papers)
            searched_sources.append("biorxiv")
            logger.info(f"Found {len(papers)} papers on biorxiv")

        if "semantic_scholar" in sources:
            logger.info("Searching Semantic Scholar...")
            papers = self._search_semantic_scholar(query, max_results_per_source)
            all_papers.extend(papers)
            searched_sources.append("semantic_scholar")
            logger.info(f"Found {len(papers)} papers on Semantic Scholar")

        # Calculate relevance scores
        query_terms = set(query.lower().split())
        for paper in all_papers:
            paper.relevance_score = self._calculate_relevance(paper, query_terms)

        # Deduplicate by title similarity
        unique_papers = []
        seen_titles = set()
        for paper in sorted(all_papers, key=lambda p: p.relevance_score, reverse=True):
            title_key = re.sub(r'[^\w]', '', paper.title.lower())[:50]
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_papers.append(paper)

        return LiteratureReport(
            query=query,
            total_found=len(unique_papers),
            papers=unique_papers,
            sources_searched=searched_sources,
        )

    def find_related_to_paper(self, paper_spec: dict, max_results: int = 20) -> LiteratureReport:
        """Find papers related to a given paper specification.

        Args:
            paper_spec: Paper specification dict
            max_results: Maximum number of papers to return

        Returns:
            LiteratureReport with related papers
        """
        # Extract keywords from paper
        keywords = []

        # From keywords field
        kw = paper_spec.get("keywords", {})
        if isinstance(kw, dict):
            kw_text = kw.get("en", "") or kw.get("ja", "")
        else:
            kw_text = str(kw)
        keywords.extend([k.strip() for k in kw_text.split(",") if k.strip()])

        # From title
        title = paper_spec.get("meta", {}).get("title", {})
        if isinstance(title, dict):
            title_text = title.get("en", "") or title.get("ja", "")
        else:
            title_text = str(title)
        keywords.extend(title_text.split()[:5])

        # Build query
        query = " ".join(keywords[:10])
        logger.info(f"Searching for papers related to: {query}")

        report = self.search(query, max_results_per_source=max_results)

        # Limit total results
        report.papers = report.papers[:max_results]
        report.total_found = len(report.papers)

        return report
