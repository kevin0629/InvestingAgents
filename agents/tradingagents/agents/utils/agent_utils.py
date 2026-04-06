from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.stock_data_tools import (
    get_stock_data,
    get_taiex_data
)

from tradingagents.agents.utils.fundamental_data_tools import (
    get_factors,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_monthly_revenue,
    get_dupont_analysis,
    get_river_chart
)
from tradingagents.agents.utils.news_data_tools import (
    get_company_news,
    get_macro_news
)
from tradingagents.agents.utils.reflection_data_tools import (
    store_reflections,
    retrieve_reflections
)
from tradingagents.agents.utils.trading_tools import create_stock_holding

__all__ = [
    "create_msg_delete",
    "get_tools",
    "get_stock_data",
    "get_taiex_data",
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
]


def get_tools(tools) -> str:
    """獲取工具名稱列表的格式化字符串，供 prompt 使用"""
    return ", ".join(getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__)) for tool in tools)


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        