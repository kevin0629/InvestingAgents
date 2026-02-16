from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_company_info(
    ticker: Annotated[str, "ticker symbol"],
) -> str:
    """
    Retrieve company information for a given ticker symbol.
    Uses the configured fundamental_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A formatted report containing company information
    """
    return route_to_vendor("get_company_info", ticker)


@tool
def get_factors(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve financial factors for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing financial factors data
    """
    return route_to_vendor("get_factors", ticker, end_date, num)

@tool
def get_balance_sheet(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve balance sheet data for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing balance sheet data
    """
    return route_to_vendor("get_balance_sheet", ticker, end_date, num)


@tool
def get_cashflow(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve cash flow statement data for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing cash flow statement data
    """
    return route_to_vendor("get_cashflow", ticker, end_date, num)


@tool
def get_income_statement(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve income statement data for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing income statement data
    """
    return route_to_vendor("get_income_statement", ticker, end_date, num)


@tool
def get_monthly_revenue(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve monthly revenue data for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing monthly revenue data
    """
    return route_to_vendor("get_monthly_revenue", ticker, end_date, num)


@tool
def get_dupont_analysis(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
    num: Annotated[int, "number of quarters to retrieve"] = 4
) -> str:
    """
    Retrieve DuPont analysis data for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
        num (int): Number of quarters to retrieve
    Returns:
        str: A formatted report containing DuPont analysis data
    """
    return route_to_vendor("get_dupont_analysis", ticker, end_date, num)

@tool
def get_river_chart(
    ticker: Annotated[str, "ticker symbol"],
    end_date: Annotated[str, "end date for data retrieval, format YYYY-MM-DD"] = None,
) -> bytes:
    """
    Retrieve river chart data for a given ticker symbol.

    Args:
        ticker (str): Ticker symbol of the company
        end_date (str): End date for data retrieval, format YYYY-MM-DD
    Returns:
        bytes: River chart data as bytes
    """
    return route_to_vendor("get_river_chart", ticker, end_date)
