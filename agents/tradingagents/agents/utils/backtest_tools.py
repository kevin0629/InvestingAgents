from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_backtest_report(
    strategy_name: Annotated[str, "name of the backtest strategy"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"]
) -> str:
    """
    Retrieve backtest report for a given strategy and end date.

    Args:
        strategy_name (str): Name of the backtest strategy
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: Backtest report content
    """
    return route_to_vendor("get_backtest_report", strategy_name, end_date)

@tool
def get_strategy() -> str:
    """
    Retrieve available backtest strategies.

    Args:
        
    Returns:
        str: Available backtest strategies
    """
    return route_to_vendor("get_strategy")