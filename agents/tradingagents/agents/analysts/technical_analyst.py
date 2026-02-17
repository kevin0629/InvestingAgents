import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from tradingagents.agents.utils.agent_utils import get_stock_data, get_taiex_data


def _safe_json(content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start:end + 1]
    return json.loads(text)


def _run_with_tools(llm, system_prompt: str, user_prompt: str, tools: List, max_steps: int = 3) -> str:
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    bound = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}

    for _ in range(max_steps):
        ai_msg = bound.invoke(messages)
        messages.append(ai_msg)
        if not getattr(ai_msg, "tool_calls", None):
            return ai_msg.content

        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_fn = tool_map[tool_name]
            try:
                tool_result = tool_fn.invoke(tool_args)
            except Exception as exc:
                tool_result = f"ToolError({tool_name}): {exc}"
            messages.append(
                ToolMessage(
                    content=str(tool_result)[:12000],
                    tool_call_id=tool_call["id"],
                )
            )

    final = llm.invoke(messages)
    return final.content


def create_market_analyst(llm):
    def market_analyst_node(state):
        plan = state.get("coordinator_plan", {})
        tasks = [
            t for t in plan.get("tasks", []) if t.get("agent") == "Technical_Analyst"
        ]
        tools = [get_stock_data, get_taiex_data]

        system_prompt = """
你是 Technical Analyst。
請依 task_type 輸出 JSON。
- ANALYSIS 請輸出：signal/confidence_score/trend_status/key_levels/technical_summary/risk_warning。
- VERIFICATION 請輸出：verification_status/reality_check/technical_flaw。
必須只輸出 JSON。
""".strip()

        reports = []
        for task in tasks:
            ticker = task.get("ticker", state.get("company_of_interest", ""))
            payload = {
                "task": task,
                "ticker": ticker,
                "trade_date": state.get("trade_date"),
            }
            try:
                content = _run_with_tools(
                    llm,
                    system_prompt,
                    json.dumps(payload, ensure_ascii=False),
                    tools,
                )
                parsed = _safe_json(content)
            except Exception as exc:
                parsed = {
                    "verification_status": "NEUTRAL"
                    if task.get("task_type") == "VERIFICATION"
                    else None,
                    "signal": "中立/觀望",
                    "confidence_score": 3,
                    "trend_status": "Data Unavailable",
                    "key_levels": {"support": None, "resistance": None},
                    "technical_summary": f"Technical analysis fallback: {exc}",
                    "risk_warning": "資料不足，需人工覆核",
                }

            reports.append(
                {
                    "ticker": ticker,
                    "task_type": task.get("task_type", "ANALYSIS"),
                    "report": parsed,
                }
            )

        return {
            "technical_reports": reports,
            "market_report": json.dumps(reports, ensure_ascii=False),
        }

    return market_analyst_node
