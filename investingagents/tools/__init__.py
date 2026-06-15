from tools.stock_data_tools import (
    get_stock_data,
    get_taiex_data
)

from tools.fundamental_data_tools import (
    get_company_info,
    get_factors,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_monthly_revenue,
    get_dupont_analysis,
    get_river_chart
)
from tools.news_data_tools import (
    get_company_news,
    get_macro_news
)
from tools.reflection_data_tools import (
    store_reflections,
    retrieve_reflections
)
from tools.trading_tools import (
    get_stock_account,
    create_stock_holding,
)
from tools.backtest_tools import (
    get_backtest_report,
    get_market_return,
    get_strategy,
)


__all__ = [
    "get_tools",
    "get_stock_data",
    "get_taiex_data",
    "get_company_info",
    "get_factors",
    "get_balance_sheet",
    "get_cashflow",
    "get_income_statement",
    "get_monthly_revenue",
    "get_dupont_analysis",
    "get_river_chart",
    "get_company_news",
    "get_macro_news",
    "store_reflections",
    "retrieve_reflections",
    "create_stock_holding",
    "get_stock_account",
    "get_backtest_report",
    "get_market_return",
    "get_strategy",
]


def get_tools(tools) -> str:
    """獲取工具名稱列表的格式化字符串，供 prompt 使用"""
    return ", ".join(getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__)) for tool in tools)