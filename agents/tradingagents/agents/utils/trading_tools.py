from langchain_core.tools import tool
from typing import Annotated
import os

@tool
def get_holdings() -> str:
    """
    Retrieve current portfolio holdings.

    Args:
        
    Returns:
        str: A formatted report containing current portfolio holdings
    """
    # Placeholder implementation, replace with actual data retrieval logic
    return "Current portfolio holdings: AAPL, MSFT, GOOGL"


@tool
def cal_return() -> str:
get