from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor
import base64


def _bytes_to_image_content(raw: bytes) -> list:
    """Convert PNG bytes to an OpenAI-compatible image_url content block list."""
    if not isinstance(raw, (bytes, bytearray)):
        return [str(raw)]
    b64 = base64.b64encode(raw).decode("utf-8")
    return [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}]


@tool
def get_stock_data(
    symbol: Annotated[str, "stock symbol of the company"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
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
    raw = route_to_vendor("get_stock_data", symbol, end_date, time_frame)
    return _bytes_to_image_content(raw)

@tool
def get_taiex_data(
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
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
    raw = route_to_vendor("get_taiex_data", end_date, time_frame)
    return _bytes_to_image_content(raw)