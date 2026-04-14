from langchain_core.tools import tool
from typing import Annotated, Optional
from tradingagents.dataflows.interface import route_to_vendor

# @tool
# def search_news(
#     query: Annotated[str, "必須以股票代號或公司名稱開頭的繁體中文搜尋關鍵字。格式：'<代號或公司> <具體業務事件>'。例如：'1436 華友聯 擴廠產能 2025'、'2724 藝舫 KY 新訂單'、'1436 華友聯 月營收 成長趨勢'。禁止使用與目標公司無關的泛用詞彙作為獨立 query。"],
#     end_date: Annotated[str, "可選的結束日期，格式 yyyy-mm-dd"] = None,
# ) -> str:
#     """
#     以繁體中文關鍵字搜尋台灣股市新聞。
#     每個搜尋 query 必須包含股票代號或公司名稱，加上具體業務關鍵字。
#     優先搜尋台灣財經新聞網站（鉅亨財經、工商時報、Digitimes 等）以提高結果相關性。

#     Args:
#         query (str): 繁體中文搜尋關鍵字，必須以股票代號或公司名稱開頭
#         end_date (str): 可選的結束日期
#     Returns:
#         str: 包含新聞搜尋結果的格式化字串
#     """
#     return route_to_vendor("search_news", query, end_date)


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



