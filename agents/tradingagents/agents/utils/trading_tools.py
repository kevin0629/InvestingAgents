from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def create_stock_holding(
    strategy: Annotated[str, "Selected stock based on the strategy"],
    orders: Annotated[str, "Order details JSON. Recommended: {\"orders\": [{\"stock\": \"2330\", \"position\": 0.3, \"buy_reason\": \"...\"}]}"],
    signal_date: Annotated[str, "Date of the trading signal"],
    reflection: Annotated[bool, "Whether to reflect on the trading decision"] = False,
) -> str:
    """
    Create stock entry signals.

    Args:
        strategy (str): Selected stock based on the strategy
        orders (str): Formatted order details. Recommended JSON format:
            {"orders": [{"stock": "2330", "position": 0.5, "buy_reason": "長期成長動能明確"}]}
        signal_date (str): Date of the trading signal
        reflection (bool): Whether to reflect on the trading decision, default is False
        
    Returns:
        str: Status message indicating the result of the stock signal creation
    """

    return route_to_vendor("create_stock_holding", strategy, orders, signal_date, reflection)