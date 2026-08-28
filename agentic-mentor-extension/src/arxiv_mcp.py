import sys
import threading
import time
import urllib.error
import urllib.request
import urllib.parse

import feedparser
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("arxiv")

ARXIV_API = "https://export.arxiv.org/api/query"
MIN_INTERVAL = 4.0

_lock = threading.Lock()
_last_call = 0.0
_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL = 600


def _throttle():
    global _last_call
    with _lock:
        wait = MIN_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()


def _query_arxiv(search_query: str, max_results: int = 5, sort_by: str = "relevance"):
    cache_key = f"{search_query}|{max_results}|{sort_by}"
    cached = _cache.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL:
        return cached[1]

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"

    last_error = None
    for attempt, delay in enumerate([0, 5, 10]):
        if delay:
            print(f"[arxiv] rate limited, retrying in {delay}s (attempt {attempt+1}/3)", file=sys.stderr, flush=True)
            time.sleep(delay)
        _throttle()
        print(f"[arxiv] requesting: {search_query}", file=sys.stderr, flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arxiv-mcp-server/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
            break
        except urllib.error.HTTPError as e:
            last_error = e
            if e.code != 429:
                raise RuntimeError(f"arxiv API error: {e}") from e
    else:
        raise RuntimeError("arxiv API rate limit hit repeatedly, try again later") from last_error

    feed = feedparser.parse(raw)

    results = []
    for entry in feed.entries:
        results.append({
            "id": entry.id.split("/abs/")[-1],
            "title": " ".join(entry.title.split()),
            "authors": [a.name for a in entry.get("authors", [])],
            "summary": " ".join(entry.summary.split()),
            "published": entry.published,
            "pdf_url": next(
                (l.href for l in entry.links if l.get("title") == "pdf"),
                entry.id.replace("/abs/", "/pdf/"),
            ),
        })

    _cache[cache_key] = (time.time(), results)
    return results


@mcp.tool()
def search_papers(query: str, max_results: int = 5) -> list[dict]:
    return _query_arxiv(f"all:{query}", max_results=max_results)


@mcp.tool()
def search_by_author(author: str, max_results: int = 5) -> list[dict]:
    return _query_arxiv(f"au:{author}", max_results=max_results)


@mcp.tool()
def get_paper_by_id(arxiv_id: str) -> dict:
    results = _query_arxiv(f"id:{arxiv_id}", max_results=1)
    if not results:
        raise ValueError(f"No paper found for id {arxiv_id}")
    return results[0]


@mcp.tool()
def recent_papers_by_category(category: str, max_results: int = 5) -> list[dict]:
    return _query_arxiv(f"cat:{category}", max_results=max_results, sort_by="submittedDate")


if __name__ == "__main__":
    mcp.run(transport="stdio")