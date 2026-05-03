from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor



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
    
    return route_to_vendor("get_company_news", company_symbol, end_date)


@tool
def get_macro_news(
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = None,
    look_back_days: Annotated[int, "Number of days to look back for news"] = 7,
) -> str:
    """
    Retrieve macro news.

    Args:
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        look_back_days (int): Number of days to look back for news, default is 7
    Returns:
        str: A formatted report containing macro news
    """
    return route_to_vendor("get_macro_news", end_date, look_back_days)



