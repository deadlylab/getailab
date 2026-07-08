"""Literature search — PubMed, arXiv, Semantic Scholar (no API keys required)."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

USER_AGENT = "GetAiLab-the example lab/1.0 (research; mailto:research@getailab.dev)"
DEFAULT_TIMEOUT = int(os.getenv("LITERATURE_SEARCH_TIMEOUT", "20"))
PUBMED_MAX = int(os.getenv("LITERATURE_PUBMED_MAX", "5"))
ARXIV_MAX = int(os.getenv("LITERATURE_ARXIV_MAX", "5"))
S2_MAX = int(os.getenv("LITERATURE_S2_MAX", "5"))


def _get(url: str, *, params: Optional[dict] = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.get(
        url,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )


def _clean_query(query: str, max_len: int = 300) -> str:
    text = re.sub(r"\s+", " ", (query or "").strip())
    return text[:max_len]


def search_pubmed(query: str, max_results: int = PUBMED_MAX) -> List[Dict[str, Any]]:
    q = _clean_query(query)
    if not q:
        return []
    try:
        esearch = _get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": q, "retmax": max_results, "retmode": "json"},
        )
        esearch.raise_for_status()
        ids = esearch.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        esummary = _get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        )
        esummary.raise_for_status()
        result = esummary.json().get("result", {})
        papers: List[Dict[str, Any]] = []
        for pmid in ids:
            item = result.get(pmid, {})
            if not item:
                continue
            papers.append({
                "source": "pubmed",
                "id": pmid,
                "title": item.get("title", ""),
                "authors": [a.get("name", "") for a in item.get("authors", [])[:4]],
                "year": (item.get("pubdate") or "")[:4],
                "journal": item.get("fulljournalname") or item.get("source", ""),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        return papers
    except Exception as exc:
        return [{"source": "pubmed", "error": str(exc)}]


def search_arxiv(query: str, max_results: int = ARXIV_MAX) -> List[Dict[str, Any]]:
    q = _clean_query(query)
    if not q:
        return []
    try:
        resp = _get(
            "http://export.arxiv.org/api/query",
            params={
                "search_query": f"all:{q}",
                "start": 0,
                "max_results": max_results,
            },
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        papers: List[Dict[str, Any]] = []
        for entry in root.findall("a:entry", ns):
            arxiv_id = (entry.findtext("a:id", default="", namespaces=ns) or "").split("/abs/")[-1]
            abstract = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
            authors = [
                (a.findtext("a:name", default="", namespaces=ns) or "")
                for a in entry.findall("a:author", ns)
            ]
            papers.append({
                "source": "arxiv",
                "id": arxiv_id,
                "title": (entry.findtext("a:title", default="", namespaces=ns) or "").replace("\n", " ").strip(),
                "authors": authors[:4],
                "year": (entry.findtext("a:published", default="", namespaces=ns) or "")[:4],
                "abstract": abstract[:1200],
                "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
            })
        return papers
    except Exception as exc:
        return [{"source": "arxiv", "error": str(exc)}]


def search_semantic_scholar(query: str, max_results: int = S2_MAX) -> List[Dict[str, Any]]:
    q = _clean_query(query)
    if not q:
        return []
    try:
        resp = _get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": q,
                "limit": max_results,
                "fields": "title,abstract,year,authors,url,externalIds",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        papers: List[Dict[str, Any]] = []
        for item in data.get("data", []):
            ext = item.get("externalIds") or {}
            papers.append({
                "source": "semantic_scholar",
                "id": item.get("paperId", ""),
                "title": item.get("title", ""),
                "authors": [a.get("name", "") for a in (item.get("authors") or [])[:4]],
                "year": item.get("year"),
                "abstract": (item.get("abstract") or "")[:1200],
                "url": item.get("url") or "",
                "doi": ext.get("DOI"),
                "pmid": ext.get("PubMed"),
            })
        return papers
    except Exception as exc:
        return [{"source": "semantic_scholar", "error": str(exc)}]


def search_literature(
    query: str,
    *,
    sources: Optional[List[str]] = None,
    max_per_source: int = 5,
) -> Dict[str, Any]:
    """Search configured literature sources and return structured + formatted results."""
    q = _clean_query(query)
    enabled = sources or ["pubmed", "arxiv", "semantic_scholar"]
    results: Dict[str, List[Dict[str, Any]]] = {}
    errors: List[str] = []

    if "pubmed" in enabled:
        pubmed = search_pubmed(q, max_results=max_per_source)
        if pubmed and pubmed[0].get("error"):
            errors.append(f"pubmed: {pubmed[0]['error']}")
            results["pubmed"] = []
        else:
            results["pubmed"] = pubmed

    if "arxiv" in enabled:
        arxiv = search_arxiv(q, max_results=max_per_source)
        if arxiv and arxiv[0].get("error"):
            errors.append(f"arxiv: {arxiv[0]['error']}")
            results["arxiv"] = []
        else:
            results["arxiv"] = arxiv

    if "semantic_scholar" in enabled:
        s2 = search_semantic_scholar(q, max_results=max_per_source)
        if s2 and s2[0].get("error"):
            errors.append(f"semantic_scholar: {s2[0]['error']}")
            results["semantic_scholar"] = []
        else:
            results["semantic_scholar"] = s2

    flat = [p for group in results.values() for p in group if not p.get("error")]
    return {
        "query": q,
        "total": len(flat),
        "results": results,
        "papers": flat,
        "errors": errors,
        "formatted": format_for_context(flat, query=q),
    }


def format_for_context(papers: List[Dict[str, Any]], *, query: str = "", max_chars: int = 12000) -> str:
    """Render papers as markdown for hypothesis-phase injection."""
    if not papers:
        return ""

    lines = ["## Literature grounding (auto-search)"]
    if query:
        lines.append(f"Query: {query}")
    lines.append("")

    for i, p in enumerate(papers, 1):
        title = p.get("title") or "Untitled"
        source = p.get("source", "unknown")
        year = p.get("year") or "?"
        authors = ", ".join(p.get("authors") or []) or "Unknown authors"
        url = p.get("url") or ""
        abstract = p.get("abstract") or ""

        block = [
            f"### [{i}] {title} ({source}, {year})",
            f"Authors: {authors}",
        ]
        if url:
            block.append(f"URL: {url}")
        if abstract:
            block.append(f"Abstract: {abstract}")
        lines.append("\n".join(block))
        lines.append("")

        if sum(len(x) for x in lines) > max_chars:
            lines.append("_(truncated — use /literature/search for full results)_")
            break

    return "\n".join(lines).strip()