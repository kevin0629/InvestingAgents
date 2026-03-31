import os
import requests
import importlib
from functools import lru_cache
from typing import Optional, Dict, Any, Literal, List
from .utils import get_backend_base_url


# Taiwanese / Chinese financial news sites — Tavily will prefer these domains
_PREFERRED_DOMAINS: List[str] = [
    "moneydj.com",        # MoneyDJ 都市財經
    "twse.com.tw",        # 證交所
    "tpex.org.tw",        # 櫃櫃
    "udn.com",            # 聯合新話網
    "ctee.com.tw",        # 工商時報
    "cna.com.tw",         # 中央社
    "technews.tw",        # 科技新報
    "ithome.com.tw",      # iThome
    "digitimes.com.tw",   # Digitimes
    "ebc.net.tw",         # 東森財經
    "stockfeel.com.tw",   # 股感
    "blueseek.com.tw",
    "wealth.com.tw",      # 財訊雙週刊
]

# Minimum Tavily relevance score — results below this are noise
MIN_SCORE_THRESHOLD = 0.7


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


def get_company_news(
    company_symbol: str,
    end_date: Optional[str] = None,
    look_back_months: int = 1,
    limit: int = 10,
) -> str:
    """
    獲取公司新聞
    
    Args:
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        look_back_months: 向前查詢的月份數，預設 1 個月
        limit: 最多返回的新聞數量，預設 10 條
    
    Returns:
        string
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/news/{company_symbol}"

    params = {
        "look_back_months": look_back_months,
        "limit": limit,
    }
    if end_date:
        params["end_date"] = end_date

    response = requests.get(url, params=params)
    response.raise_for_status()

    payload = response.json()
    data = payload.get("news_data", [])
    message = payload.get("message")
    if not data:
        return message or "查不到新聞"

    sections = []
    for item in data:
        title = item.get("title", "(無標題)")
        published_at = item.get("published_at", "")
        content = item.get("content", "").strip() or "(無內容)"
        sections.append(
            f"## {title}\n"
            f"### {published_at}\n"
            f"### {content}"
        )

    return "\n".join(sections)

def get_macro_news(
    end_date: Optional[str] = None,
    look_back_days: int = 1,
    limit: int = 200,
) -> str:
    """Fetch macro news from the backend API."""
    base_url = get_backend_base_url()
    url = f"{base_url}/news/macro"

    params = {
        "look_back_days": look_back_days,
        "limit": limit,
    }
    if end_date:
        params["end_date"] = end_date

    response = requests.get(url, params=params)
    response.raise_for_status()

    payload = response.json()
    data = payload.get("news_data", [])
    message = payload.get("message")
    if not data:
        return message or "查不到新聞"

    sections = []
    for item in data:
        title = item.get("title", "(無標題)")
        published_at = item.get("published_at", "")
        content = item.get("content", "").strip() or "(無內容)"
        sections.append(
            f"## {title}\n"
            f"### {published_at}\n"
            f"### {content}"
        )

    return "\n".join(sections)


def search_news(
    query: str,
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic",
    max_results: int = 5,
    end_date: Optional[str] = None,
    min_score: float = MIN_SCORE_THRESHOLD,
) -> Dict[str, Any]:
    """
    使用 Tavily SDK 搜尋新聞
    
    Args:
        query: 搜尋關鍵字，例如 "輝達 2330 擴廠"
        search_depth: 搜尋深度，預設 "basic"
        max_results: 最多返回結果數，預設 5
        end_date: 指定搜尋的結束日期 (YYYY-MM-DD format)，None 表示不限制
        min_score: 返回結果的最低相關性分數，低於此分數的結果將被過濾掉
    Returns:
        包含新聞搜尋結果的字典
    Raises:
        RuntimeError: If Tavily request fails
        ValueError: If TAVILY_API_KEY not found
    """
    client = get_tavily_client()

    try:
        response = client.search(
            query=query,
            topic="news",
            search_depth=search_depth,
            max_results=max_results,
            end_date=end_date,
            include_answer=False,
            include_raw_content=False,
            include_images=False,
            include_domains=_PREFERRED_DOMAINS,
        )
    except Exception:
        # Fallback: retry without domain filter (some Tavily plans don't support it)
        try:
            response = client.search(
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

    # Filter out low-relevance results
    results = response.get("results", [])
    filtered = [r for r in results if (r.get("score") or 0) >= min_score]
    response["results"] = filtered
    return response


def search_news_for_agent(
    query: str,
    end_date: Optional[str] = None,
) -> str:
    """Return Tavily news search results in an LLM-friendly markdown string."""
    response = search_news(
        query=query,
        search_depth="basic",
        max_results=5,
        end_date=end_date,
        min_score=MIN_SCORE_THRESHOLD,
    )

    results = response.get("results", [])
    if not results:
        return (
            f"查詢「{query}」未找到相關性足夠高的新聞結果。"
            f"建議改用更具體的中文關鍵字並包含股票代號或公司名稱。"
        )

    lines = [f"## 新聞搜尋結果：{query}", ""]

    for index, item in enumerate(results, start=1):
        title   = item.get("title", "(無標題)")
        content = item.get("content", "").strip()
        score   = item.get("score", 0)
        pub     = item.get("published_date", "")

        lines.append(f"### {index}. {title}")
        if pub:
            lines.append(f"- 發佈日期: {pub}  | 相關度: {score:.3f}")
        else:
            lines.append(f"- 相關度: {score:.3f}")
        if content:
            lines.append(f"{content}")
        lines.append("")

    return "\n".join(lines)