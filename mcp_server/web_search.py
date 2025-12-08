# mcp_server/web_search.py
import os
import time
import logging
from typing import Dict, Any, List, Tuple
import requests

logger = logging.getLogger(__name__)

WEB_SEARCH_API_URL = os.getenv("WEB_SEARCH_API_URL", "https://google.serper.dev/search")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")

CACHE_TTL_SECONDS = 180
MIN_INTERVAL_SECONDS = 1.0

_cache: Dict[Tuple[str, int], Tuple[float, Dict[str, Any]]] = {}
_last_call_ts: float = 0.0


def _rate_limit():
    global _last_call_ts
    now = time.time()
    if now - _last_call_ts < MIN_INTERVAL_SECONDS:
        time.sleep(MIN_INTERVAL_SECONDS - (now - _last_call_ts))
    _last_call_ts = time.time()


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Serper.dev web search (Google SERP API)."""
    if not WEB_SEARCH_API_KEY:
        raise ValueError("WEB_SEARCH_API_KEY not set")

    cache_key = (query, max_results)
    now = time.time()

    # Cache check
    if cache_key in _cache:
        ts, payload = _cache[cache_key]
        if now - ts <= CACHE_TTL_SECONDS:
            return payload

    _rate_limit()

    headers = {
        "X-API-KEY": WEB_SEARCH_API_KEY,
        "Content-Type": "application/json",
    }

    body = {
        "q": query,
        "num": max_results
    }

    logger.info(f"[web.search] calling Serper for query={query}")

    resp = requests.post(WEB_SEARCH_API_URL, json=body, headers=headers)
    resp.raise_for_status()
    data = resp.json()

    # Normalize Serper response
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "price": None,
            "availability": None,
        })

    payload = {
        "results": results,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    _cache[cache_key] = (now, payload)
    return payload
