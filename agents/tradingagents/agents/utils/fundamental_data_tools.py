from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_company_info(
    symbol: Annotated[str, "stock symbol of the company"],
) -> str:
    """
    Retrieve company information for a given symbol symbol.
    Uses the configured fundamental_data vendor.
    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
    Returns:
        str: A formatted report containing company information
    """
    return route_to_vendor("get_company_info", symbol)


@tool
def get_factors(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve financial factors for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing financial factors data
    """
    return route_to_vendor("get_factors", symbol, end_date, num)

@tool
def get_balance_sheet(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve balance sheet data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing balance sheet data
    """
    return route_to_vendor("get_balance_sheet", symbol, end_date, num)


@tool
def get_cashflow(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve cash flow statement data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing cash flow statement data
    """
    return route_to_vendor("get_cashflow", symbol, end_date, num)


@tool
def get_income_statement(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve income statement data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing income statement data
    """
    return route_to_vendor("get_income_statement", symbol, end_date, num)


@tool
def get_monthly_revenue(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve monthly revenue data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing monthly revenue data
    """
    return route_to_vendor("get_monthly_revenue", symbol, end_date, num)


@tool
def get_dupont_analysis(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve DuPont analysis data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing DuPont analysis data
    """
    return route_to_vendor("get_dupont_analysis", symbol, end_date, num)

@tool
def get_river_chart(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> bytes:
    """
    Retrieve river chart data for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        bytes: River chart data as bytes
    """
    return route_to_vendor("get_river_chart", symbol, end_date)
