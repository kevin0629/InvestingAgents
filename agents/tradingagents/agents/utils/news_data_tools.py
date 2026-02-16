from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def search_news(
    query: Annotated[str, "News search query, e.g. 'TSMC earnings and guidance'"],
    max_results: Annotated[int, "Maximum number of results to return"] = 5,
    end_date: Annotated[str, "Optional end date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve news data for a given query.

    Args:
        query (str): News search query
        max_results (int): Maximum number of results to return
        end_date (str): Optional end date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    return route_to_vendor("search_news", query, max_results, end_date)
