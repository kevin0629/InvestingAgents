from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def create_stock_holding(
    strategy: Annotated[str, "Selected stock based on the strategy"],
    orders: Annotated[
        str,
        (
            "Order details JSON. Recommended: {\"orders\": [{\"stock\": \"2330\", \"position\": 0.3, \"buy_reason\": \"...\", \"growth_score\": 8, \"value_score\": 6, \"turnaround_score\": 4}]}. "
            "buy_reason must be a single integrated assessment from Financial + Technical + News, and macro context must be woven into these three dimensions. "
            "growth_score/value_score/turnaround_score are KPI scores (0-10 integers) derived from the integrated analysis content. "
            "Example buy_reason: 『財務面顯示毛利率與現金流改善，技術面站上中長期均線且量能放大，新聞面顯示客戶拉貨與訂單能見度提升；"
            "在景氣溫和復甦與政策支持先進製程的宏觀環境下，三面向訊號一致，因此給予買進評級。』"
        ),
    ],
    signal_date: Annotated[str, "Date of the trading signal"],
    reflection: Annotated[bool, "Whether to reflect on the trading decision"] = False,
) -> str:
    """
    Create stock entry signals.

    Args:
        strategy (str): Selected stock based on the strategy
        orders (str): Formatted order details. Fixed JSON format:
            {"orders": [{"stock": "2330", "position": 0.5, "buy_reason": "context...", "growth_score": 8, "value_score": 6, "turnaround_score": 4}]}
            buy_reason should be one coherent rationale that integrates:
            - Financial evidence
            - Technical evidence
            - News evidence
            - Macro context embedded into the three evidences above
            KPI fields should be included for each stock:
            - growth_score (int, 0-10): Quantified growth KPI from the analysis
            - value_score (int, 0-10): Quantified value KPI from the analysis
            - turnaround_score (int, 0-10): Quantified turnaround KPI from the analysis
        signal_date (str): Date of the trading signal
        reflection (bool): Whether to reflect on the trading decision
        
    Returns:
        str: Status message indicating the result of the stock signal creation
    """

    return route_to_vendor("create_stock_holding", strategy, orders, signal_date, reflection)