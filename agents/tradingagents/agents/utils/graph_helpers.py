"""
Shared helper nodes used across all analyst subgraphs.

- clear_messages         : 清除 state 中的所有 messages，達到 agent 間的 context 隔離效果
- handle_image_tool_results : 修復 OpenAI 不允許在 ToolMessage 內放 image_url 的問題
"""

import json
from langchain_core.messages import HumanMessage, ToolMessage, RemoveMessage


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
