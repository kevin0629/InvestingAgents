import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger

from tradingagents.agents.utils.agent_utils import search_news, get_company_info


def _safe_json(content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start:end + 1]
    return json.loads(text)


def _run_with_tools(
    llm,
    system_prompt: str,
    user_prompt: str,
    tools: List,
    run_id: str,
    node_name: str,
    max_steps: int = 4,
) -> str:
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    bound = llm.bind_tools(tools)
    tool_map = {tool.name: tool for tool in tools}

    for _ in range(max_steps):
        ai_msg = bound.invoke(messages)
        AgentExecutionLogger.log_event(
            run_id,
            "llm_output",
            node_name,
            {
                "content": ai_msg.content,
                "reasoning_trace": getattr(ai_msg, "reasoning_content", None)
                or getattr(ai_msg, "additional_kwargs", {}).get("reasoning"),
            },
        )
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
            AgentExecutionLogger.log_event(
                run_id,
                "tool_call",
                node_name,
                {"tool": tool_name, "args": tool_args, "result": str(tool_result)[:6000]},
            )
            messages.append(
                ToolMessage(
                    content=str(tool_result)[:12000],
                    tool_call_id=tool_call["id"],
                )
            )

    final = llm.invoke(messages)
    return final.content


def create_news_analyst(llm):
    def news_analyst_node(state):
        run_id = state.get("run_id", "")
        AgentExecutionLogger.log_event(run_id, "node_start", "News Analyst", {"coordinator_plan": state.get("coordinator_plan", {})})
        plan = state.get("coordinator_plan", {})
        tasks = [t for t in plan.get("tasks", []) if t.get("agent") == "News_Analyst"]
        tools = [get_company_info, search_news]

        system_prompt = """
你是 News Analyst。你必須主動使用 search_news 工具。
請依 task_type 輸出 JSON：
- ANALYSIS: signal/confidence_score/impact_timeline/key_findings/risk_factors/source_links。
- VERIFICATION: verification_status/reality_check/news_evidence/source_links。
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
                    run_id,
                    "News Analyst",
                )
                parsed = _safe_json(content)
                if "source_links" not in parsed:
                    parsed["source_links"] = []
            except Exception as exc:
                parsed = {
                    "signal": "中性",
                    "confidence_score": 3,
                    "impact_timeline": "Unclear",
                    "key_findings": {"summary": f"News analysis fallback: {exc}"},
                    "risk_factors": "資料不足，需人工覆核",
                    "source_links": [],
                }

            reports.append(
                {
                    "ticker": ticker,
                    "task_type": task.get("task_type", "ANALYSIS"),
                    "report": parsed,
                }
            )

        AgentExecutionLogger.log_event(
            run_id,
            "node_output",
            "News Analyst",
            {"news_reports": reports},
        )
        return {
            "news_reports": reports,
            "news_report": json.dumps(reports, ensure_ascii=False),
        }

    return news_analyst_node
