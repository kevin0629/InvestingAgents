import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger

from tradingagents.agents.utils.agent_utils import (
    get_balance_sheet,
    get_cashflow,
    get_company_info,
    get_dupont_analysis,
    get_factors,
    get_income_statement,
    get_monthly_revenue,
    get_river_chart,
)


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


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        run_id = state.get("run_id", "")
        AgentExecutionLogger.log_event(run_id, "node_start", "Fundamental Analyst", {"coordinator_plan": state.get("coordinator_plan", {})})
        plan = state.get("coordinator_plan", {})
        tasks = [t for t in plan.get("tasks", []) if t.get("agent") == "Fundamental_Analyst"]
        tools = [
            get_company_info,
            get_factors,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_monthly_revenue,
            get_dupont_analysis,
            get_river_chart,
        ]

        system_prompt = """
你是 Fundamental Analyst。
請依 task_type 產出 JSON：
- ANALYSIS: 評估成長、風險、估值位階，輸出 signal/confidence/valuation/key_observations/financial_anomaly/investment_thesis。
- VERIFICATION: 驗證 past_rationale 是否兌現，再補前瞻分析，輸出包含 verification + analysis。
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
                    "Fundamental Analyst",
                )
                parsed = _safe_json(content)
            except Exception as exc:
                parsed = {
                    "ticker": ticker,
                    "is_holding": task.get("task_type") == "VERIFICATION",
                    "verification": None,
                    "analysis": {
                        "signal": "中立/觀望",
                        "valuation": "Unknown",
                        "reasoning": f"Fundamental analysis fallback: {exc}",
                        "risk_alert": "資料不足，需人工覆核",
                    },
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
            "Fundamental Analyst",
            {"fundamental_reports": reports},
        )
        return {
            "financial_reports": reports,
            "fundamentals_report": json.dumps(reports, ensure_ascii=False),
        }

    return fundamentals_analyst_node
