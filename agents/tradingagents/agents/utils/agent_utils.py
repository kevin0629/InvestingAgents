import json
from langchain_core.messages import HumanMessage, ToolMessage, RemoveMessage

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
    "clear_messages",
    "handle_image_tool_results",
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


def clear_messages(state) -> dict:
    """清除所有 messages，防止 agent 之間的 context 洩漏。
    放在 subgraph 的第一個 node 可確保下一個 agent 拿到乾淨的 messages 起點。
    """
    msgs = state.get("messages") or []
    if not msgs:
        return {}
    return {"messages": [RemoveMessage(id=m.id) for m in msgs]}


def handle_image_tool_results(state) -> dict:
    """
    OpenAI does not allow image_url in tool-role messages.
    Strip image blocks from each ToolMessage (update in-place by reusing its id),
    then append a HumanMessage carrying the images so the LLM can still see them.
    Updating by same id keeps the ToolMessage in its original position so the
    sequence AIMessage(tool_calls) → ToolMessage(s) stays valid.
    """
    messages = state["messages"]
    updates = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content
        # ToolNode may serialise list content to a JSON string; handle both
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    content = parsed
            except Exception:
                pass

        if not isinstance(content, list):
            continue

        image_blocks = [
            b for b in content
            if isinstance(b, dict) and b.get("type") == "image_url"
        ]
        if not image_blocks:
            continue

        text_blocks = [
            b for b in content
            if not (isinstance(b, dict) and b.get("type") == "image_url")
        ]
        plain_text = " ".join(
            b["text"] if isinstance(b, dict) and "text" in b else str(b)
            for b in text_blocks
        ) or "圖表已提供。"

        # Update ToolMessage in-place (same id → add_messages replaces, not appends)
        updates.append(ToolMessage(
            id=msg.id,
            content=plain_text,
            tool_call_id=msg.tool_call_id,
            name=msg.name,
        ))
        # Append image as a new user turn AFTER the (now-clean) ToolMessage
        updates.append(HumanMessage(
            content=image_blocks + [{"type": "text", "text": f"{msg.name} 工具返回的圖表如上，請分析。"}]
        ))

    return {"messages": updates} if updates else {}

        