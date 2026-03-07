"""
Web Search Tool architecture for MAARC.
Supports multiple providers via a clean interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger("engine.tools")

class SearchProvider(ABC):
    """Abstract base class for search providers."""
    
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> str:
        """Perform a search and return formatted results."""
        pass


class DuckDuckGoProvider(SearchProvider):
    """Implementation using duckduckgo-search."""
    
    def search(self, query: str, max_results: int = 5) -> str:
        from duckduckgo_search import DDGS
        try:
            logger.info(f"[cyan]DDG Search:[/cyan] {query}")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
            if not results:
                return "No results found."
                
            formatted = []
            for i, res in enumerate(results, 1):
                title = res.get("title", "No Title")
                snippet = res.get("body", "No Snippet")
                link = res.get("href", "No Link")
                formatted.append(f"{i}. {title}\nSnippet: {snippet}\nSource: {link}\n")
            
            return "\n".join(formatted)
        except Exception as e:
            logger.error(f"DDG Search error: {str(e)}")
            return f"Error: {str(e)}"


# Define the tool metadata for LangChain
from langchain_core.tools import tool

def get_search_tool(config: Optional[Dict[str, Any]] = None):
    """
    Factory function to create the search tool based on configuration.
    """
    # Default to DDG if not specified
    provider_type = "duckduckgo"
    max_results = 5
    
    if config:
        search_cfg = config.get("research", {}).get("web_search", {})
        provider_type = search_cfg.get("provider", "duckduckgo").lower()
        max_results = search_cfg.get("max_results", 5)

    # Initialize the provider
    if provider_type == "duckduckgo":
        provider = DuckDuckGoProvider()
    # Add more providers here (e.g., searxng)
    # elif provider_type == "searxng":
    #     provider = SearXNGProvider()
    else:
        logger.warning(f"Unknown search provider '{provider_type}', falling back to DuckDuckGo")
        provider = DuckDuckGoProvider()

    @tool
    def search_tool(query: str) -> str:
        """Search the web for current or grounded information on a topic."""
        return provider.search(query, max_results=max_results)
    
    return search_tool


# Legacy support (may be removed later)
def web_search(query: str, max_results: int = 5) -> str:
    """Old interface, using DDG by default."""
    return DuckDuckGoProvider().search(query, max_results)

# Backwards compatible export for AgentNode
search_tool = get_search_tool()
