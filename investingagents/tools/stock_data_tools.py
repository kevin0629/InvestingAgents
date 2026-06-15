from langchain_core.tools import tool
import requests
from typing import Annotated
import os
from .utils import bytes2image



BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

@tool
def get_taiex_data(
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = None,
    time_frame: Annotated[str, "Time frame for stock data (e.g. 'D', 'W', 'M')"] = "D"
) -> list:
    """
    Retrieve TAIEX index data (OHLCV) and indicator data (MA20、MA60、MA240).

    Args:
        end_date (str): End date in yyyy-mm-dd format
        time_frame (str): Time frame for stock data (e.g. 'D', 'W', 'M')
    Returns:
        list: Multimodal content block containing the chart image for the LLM to interpret.
    """
    url = f"{BASE_URL}/stock/taiex/chart"
    
    params = {"timeframe": time_frame}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return bytes2image(response.content)

@tool
def get_stock_data(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = None,
    time_frame: Annotated[str, "Time frame for stock data (e.g. 'D', 'W', 'M')"] = "D"
) -> list:
    """
    Retrieve stock price data (OHLCV) and indicator data (MA20、MA60、MA240、BBAND、MACD、RSI) for a given stock symbol.

    Args:
        symbol (str): Stock symbol of the company, e.g. 2330, 2455, 3491
        end_date (str): End date in yyyy-mm-dd format
        time_frame (str): Time frame for stock data (e.g. 'D', 'W', 'M')
    Returns:
        list: Multimodal content block containing the chart image for the LLM to interpret.
    """
    url = f"{BASE_URL}/stock/{symbol}/chart"
    
    params = {"timeframe": time_frame}
    if end_date:
        params["end_date"] = end_date
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    return bytes2image(response.content)