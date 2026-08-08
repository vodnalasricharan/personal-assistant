from __future__ import annotations

"""
Optional web search tool.
Requires WEB_SEARCH_ENABLED=true and a supported search API.
Currently a no-op placeholder; extend with SerpAPI / DuckDuckGo as needed.
"""

from typing import Any

from config.settings import Settings


def web_search(query: str, settings: Settings) -> dict[str, Any]:
    """
    Search the web for information.

    Not enabled by default.  Set WEB_SEARCH_ENABLED=true and integrate
    a search API (SerpAPI, Tavily, DuckDuckGo) to enable.
    """
    if not settings.web_search_enabled:
        return {
            "success": False,
            "results": [],
            "message": "Web search is disabled. Set WEB_SEARCH_ENABLED=true in .env to enable.",
        }
    # Placeholder: return empty results when enabled but no API configured.
    return {
        "success": True,
        "results": [],
        "message": "Web search enabled but no search provider is configured.",
    }
