import requests
from typing import Optional
from .utils import get_backend_base_url
from datetime import datetime



MIN_SCORE_THRESHOLD = 0.7

def get_company_news(
    company_symbol: str,
    end_date: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    獲取公司新聞
    
    Args:
        company_symbol: 股票代號，例如 "2330", "2455", "3491"
        end_date: 結束日期 (YYYY-MM-DD format), 如果為 None 則使用最新資料
        limit: 最多返回的新聞數量，預設 10 條
    
    Returns:
        string
        
    Raises:
        requests.HTTPError: If API request fails
    """
    base_url = get_backend_base_url()
    url = f"{base_url}/news/{company_symbol}"

    params = {
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
        published_at = datetime.fromisoformat(published_at).strftime("%Y-%m-%d") if published_at else ""
        content = item.get("content", "").strip() or "(無內容)"
        sections.append(
            f"## {title}\n"
            f"### {published_at}\n"
            f"### {content}"
        )

    return "\n".join(sections)

def get_macro_news(
    end_date: Optional[str] = None,
    look_back_days: int = 7,
    limit: int = 100,
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
        published_at = datetime.fromisoformat(published_at).strftime("%Y-%m-%d") if published_at else ""
        content = item.get("content", "").strip() or "(無內容)"
        sections.append(
            f"## {title}\n"
            f"### {published_at}\n"
            f"### {content}"
        )

    return "\n".join(sections)



if __name__ == "__main__":
    # print(get_company_news("2455", "2024-06-01", look_back_days=90))
    print(get_macro_news("2024-06-01", look_back_days=1))