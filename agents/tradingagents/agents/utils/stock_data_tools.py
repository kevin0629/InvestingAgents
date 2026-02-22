from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_stock_data(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    time_frame: Annotated[str, "Time frame for stock data (e.g. 'D', 'W', 'M')"] = "D"
) -> bytes:
    """
    Retrieve stock price data (OHLCV) and indicator data (MA20、MA60、MA240、BBAND、MACD、RSI) for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date in yyyy-mm-dd format
        time_frame (str): Time frame for stock data (e.g. 'D', 'W', 'M')
    Returns:
        bytes: PNG image bytes rendering stock price and indicator data for the specified stock symbol in the specified date range.
    """
    return route_to_vendor("get_stock_data", symbol, end_date, time_frame)

@tool
def get_taiex_data(
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    time_frame: Annotated[str, "Time frame for stock data (e.g. 'D', 'W', 'M')"] = "D"
) -> bytes:
    """
    Retrieve TAIEX index data (OHLCV) and indicator data (MA20、MA60、MA240).

    Args:
        end_date (str): End date in yyyy-mm-dd format
        time_frame (str): Time frame for stock data (e.g. 'D', 'W', 'M')
    Returns:
        bytes: PNG image bytes rendering TAIEX index data and indicator data for the specified date range.
    """
    return route_to_vendor("get_taiex_data", end_date, time_frame)