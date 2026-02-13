import requests
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


def get_tavily_api_key() -> str:
    """Get Tavily API key from environment."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables")
    return api_key


def search_news(
    query: str,
    search_depth: str = "basic",
    max_results: int = 5,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    days: Optional[int] = None
) -> Dict[str, Any]:
    """
    使用 Tavily API 搜尋新聞
    
    Args:
        query: 搜尋關鍵字，例如 "台積電 TSMC"
        search_depth: 搜尋深度，"basic" 或 "advanced"
        max_results: 最多返回結果數，預設 5
        include_domains: 指定要搜尋的網域列表
        exclude_domains: 排除的網域列表
        days: 搜尋最近幾天的新聞，None 表示不限制
        
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
        requests.HTTPError: If API request fails
        ValueError: If TAVILY_API_KEY not found
    """
    api_key = get_tavily_api_key()
    url = "https://api.tavily.com/search"
    
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
    }
    
    if include_domains:
        payload["include_domains"] = include_domains
    
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    
    if days is not None:
        # Calculate the date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        payload["days"] = days
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()


def search_company_news(
    company_symbol: str,
    company_name: Optional[str] = None,
    max_results: int = 5,
    days: int = 7,
    search_depth: str = "basic"
) -> Dict[str, Any]:
    """
    搜尋特定公司的新聞
    
    Args:
        company_symbol: 股票代碼，例如 "2330"
        company_name: 公司名稱，例如 "台積電" 或 "TSMC"，如果為 None 則只用代碼搜尋
        max_results: 最多返回結果數，預設 5
        days: 搜尋最近幾天的新聞，預設 7 天
        search_depth: 搜尋深度，"basic" 或 "advanced"
        
    Returns:
        包含新聞搜尋結果的字典
        
    Raises:
        requests.HTTPError: If API request fails
        ValueError: If TAVILY_API_KEY not found
    """
    # Build search query
    if company_name:
        query = f"{company_name} {company_symbol} stock news"
    else:
        query = f"{company_symbol} stock news"
    
    return search_news(
        query=query,
        search_depth=search_depth,
        max_results=max_results,
        days=days
    )


def search_market_news(
    market: str = "Taiwan",
    max_results: int = 10,
    days: int = 1,
    search_depth: str = "basic"
) -> Dict[str, Any]:
    """
    搜尋市場相關新聞
    
    Args:
        market: 市場名稱，例如 "Taiwan", "US", "China"
        max_results: 最多返回結果數，預設 10
        days: 搜尋最近幾天的新聞，預設 1 天
        search_depth: 搜尋深度，"basic" 或 "advanced"
        
    Returns:
        包含新聞搜尋結果的字典
        
    Raises:
        requests.HTTPError: If API request fails
        ValueError: If TAVILY_API_KEY not found
    """
    query = f"{market} stock market news"
    
    return search_news(
        query=query,
        search_depth=search_depth,
        max_results=max_results,
        days=days
    )


def search_industry_news(
    industry: str,
    max_results: int = 10,
    days: int = 7,
    search_depth: str = "basic"
) -> Dict[str, Any]:
    """
    搜尋產業相關新聞
    
    Args:
        industry: 產業名稱，例如 "semiconductor", "電子業", "金融業"
        max_results: 最多返回結果數，預設 10
        days: 搜尋最近幾天的新聞，預設 7 天
        search_depth: 搜尋深度，"basic" 或 "advanced"
        
    Returns:
        包含新聞搜尋結果的字典
        
    Raises:
        requests.HTTPError: If API request fails
        ValueError: If TAVILY_API_KEY not found
    """
    query = f"{industry} industry news"
    
    return search_news(
        query=query,
        search_depth=search_depth,
        max_results=max_results,
        days=days
    )
