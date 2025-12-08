# mcp_client.py
from typing import Dict, Any
import requests
import os

MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://localhost:8000")


def call_rag_tool(query: str, constraints: Dict[str, Any] | None = None, max_results: int = 5):
    url = f"{MCP_BASE_URL}/mcp/tools/rag.search"
    payload = {
        "query": query,
        "constraints": constraints or {},
        "max_results": max_results,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json().get("results", [])


def call_web_tool(query: str, max_results: int = 3):
    url = f"{MCP_BASE_URL}/mcp/tools/web.search"
    payload = {
        "query": query,
        "max_results": max_results,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json().get("results", [])
