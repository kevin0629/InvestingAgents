from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def search_news(
    query: Annotated[str, "必須以股票代號或公司名稱開頭的繁體中文搜尋關鍵字。格式：'<代號或公司> <具體業務事件>'。例如：'1436 華友聯 擴廠產能 2025'、'2724 藝舫 KY 新訂單'、'1436 華友聯 月營收 成長趨勢'。禁止使用與目標公司無關的泛用詞彙作為獨立 query。"],
    end_date: Annotated[str, "可選的結束日期，格式 yyyy-mm-dd"] = None,
) -> str:
    """
    以繁體中文關鍵字搜尋台灣股市新聞。
    每個搜尋 query 必須包含股票代號或公司名稱，加上具體業務關鍵字。
    優先搜尋台灣財經新聞網站（鉅亨財經、工商時報、Digitimes 等）以提高結果相關性。

    Args:
        query (str): 繁體中文搜尋關鍵字，必須以股票代號或公司名稱開頭
        end_date (str): 可選的結束日期
    Returns:
        str: 包含新聞搜尋結果的格式化字串
    """
    return route_to_vendor("search_news", query, end_date)


@tool
def get_company_news(
    company_symbol: Annotated[str, "股票代號或公司名稱"],
    end_date: Annotated[str, "可選的結束日期，格式 yyyy-mm-dd"] = None,
    look_back_months: Annotated[int, "向前查詢的月份數，預設 1"] = 1,
) -> str:
    """
    取得指定公司的新聞摘要。

    Args:
        company_symbol (str): 股票代號或公司名稱，例如 2330、台積電
        end_date (str): 可選的結束日期 (YYYY-MM-DD)
        look_back_months (int): 向前查詢的月份數
    Returns:
        str: 格式化的新聞列表
    """
    return route_to_vendor("get_company_news", company_symbol, end_date, look_back_months)


@tool
def get_macro_news(
    end_date: Annotated[str, "可選的結束日期，格式 yyyy-mm-dd"] = None,
    look_back_days: Annotated[int, "向前查詢的天數，預設 1"] = 1,
) -> str:
    """
    取得總體/大盤相關新聞摘要。

    Args:
        end_date (str): 可選的結束日期 (YYYY-MM-DD)
        look_back_days (int): 向前查詢的天數
    Returns:
        str: 格式化的新聞列表
    """
    return route_to_vendor("get_macro_news", end_date, look_back_days)



