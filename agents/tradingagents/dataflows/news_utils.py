import os
import importlib
from functools import lru_cache
from typing import Optional, Dict, Any, Literal


def get_tavily_api_key() -> str:
    """Get Tavily API key from environment."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables")
    return api_key


@lru_cache(maxsize=1)
def get_tavily_client() -> Any:
    """Create and cache a Tavily client instance."""
    tavily_module = importlib.import_module("tavily")
    tavily_client_cls = getattr(tavily_module, "TavilyClient")
    return tavily_client_cls(api_key=get_tavily_api_key())


def search_news(
    query: str,
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic",
    max_results: int = 5,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    使用 Tavily SDK 搜尋新聞
    
    Args:
        query: 搜尋關鍵字，例如 "台積電 TSMC"
        search_depth: 搜尋深度，"basic" 或 "advanced"
        max_results: 最多返回結果數，預設 5
        end_date: 指定搜尋的結束日期 (YYYY-MM-DD format)，None 表示不限制
    Returns:
        包含新聞搜尋結果的字典，格式：
        {
            "query": str,
            "results": [
                {
                    "title": str,
                    "url": str,
                    "content": str,
                    "score": float,
                    "published_date": str
                },
                ...
            ]
        }
        
    Raises:
        RuntimeError: If Tavily request fails
        ValueError: If TAVILY_API_KEY not found
    """
    client = get_tavily_client()

    try:
        return client.search(
            query=query,
            topic="news",
            search_depth=search_depth,
            max_results=max_results,
            end_date=end_date,
            include_answer=False,
            include_raw_content=False,
            include_images=False,
        )
    except Exception as exc:
        raise RuntimeError(f"Tavily search failed: {exc}") from exc


def search_news_for_agent(
    query: str,
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic",
    max_results: int = 5,
    end_date: Optional[str] = None,
) -> str:
    """Return Tavily news search results in an LLM-friendly markdown string."""
    response = search_news(
        query=query,
        search_depth=search_depth,
        max_results=max_results,
        end_date=end_date,
    )

    results = response.get("results", [])
    answer = response.get("answer", "")
    if not results:
        return f"No Tavily news results found for query: {query}"

    lines = [f"## Tavily News Results for: {query}", ""]
    if answer:
        lines.append(f"### Answer: {answer}")
        lines.append("")

    for index, item in enumerate(results, start=1):
        title = item.get("title", "No title")
        url = item.get("url", "")
        content = item.get("content", "")
        score = item.get("score")
 
        lines.append(f"### {index}. {title}")
        lines.append(f"- URL: {url or 'N/A'}")
        if score is not None:
            lines.append(f"- Score: {score}")
        if content:
            lines.append(f"- Summary: {content}")
        lines.append("")

    return "\n".join(lines)