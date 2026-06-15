from langchain_core.tools import tool
import requests
from typing import Annotated
import os
from datetime import datetime



BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

@tool
def get_company_news(
    company_symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve company news for a given symbol symbol.

    Args:
        company_symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing company news
    """
    url = f"{BASE_URL}/news/{company_symbol}"

    params = {}
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


@tool
def get_macro_news(
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve macro news.

    Args:
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        str: A formatted report containing macro news
    """
    url = f"{BASE_URL}/news/macro"

    params = {}
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