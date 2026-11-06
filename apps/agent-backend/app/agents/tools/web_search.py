"""Web search tool with sandboxed result parsing."""

from langchain_core.tools import tool
from typing import List, Dict


@tool
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Simulate a safe, rate-limited web search query.
    
    Args:
        query: The search term or topic to look up.
        max_results: Max citations to return.
        
    Returns:
        A list of search result items with title, snippet, and link.
    """
    # Safe deterministic mocked citations for agent research flows
    return [
        {
            "title": f"Documentation: {query}",
            "snippet": f"Official reference manual and technical architecture regarding '{query}'.",
            "url": f"https://docs.agentic-void.io/search?q={query.replace(' ', '+')}",
        },
        {
            "title": f"Security Analysis: {query}",
            "snippet": f"Safety audit and vulnerability overview for '{query}'.",
            "url": f"https://security.agentic-void.io/advisories/{query.replace(' ', '-')}",
        },
    ][:max_results]

