import json
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger
from tradingagents.agents.utils.agent_utils import retrieve_reflections


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
    max_steps: int = 5,
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
            messages.append(ToolMessage(content=str(tool_result)[:12000], tool_call_id=tool_call["id"]))

    final = llm.invoke(messages)
    return final.content


def create_portfolio_manager(llm):
    def portfolio_manager_node(state):
        run_id = state.get("run_id", "")
        mode = str(state.get("mode", "single")).upper()
        market_regime = state.get("market_regime", "Neutral")
        tools = [retrieve_reflections]
        AgentExecutionLogger.log_event(
            run_id,
            "node_start",
            "Portfolio Manager",
            {"mode": mode, "market_regime": market_regime},
        )

        analysis_reports = {
            "financial": state.get("financial_reports", []),
            "technical": state.get("technical_reports", []),
            "news": state.get("news_reports", []),
        }
        reflections = state.get("critic_reflections", [])
        current_holdings = state.get("current_holdings", [])

        system_prompt = """
你是 Portfolio Manager。
你必須輸出 JSON，並根據 market_regime 動態調整權重，處理訊號衝突，使用 critic reflection 修正決策。
你可以使用 retrieve_reflections 工具取得歷史反思，並在決策時明確反映這些經驗。

SINGLE 模式輸出：
{
  "ticker": "",
  "final_action": "Buy|Sell|Hold",
  "confidence_score": 0,
  "market_regime_adjustment": "",
  "reflection_applied": "",
  "reasoning_summary": "",
  "risk_alert": ""
}

BATCH 模式輸出：
{
  "portfolio_decisions": [
    {
      "ticker": "",
      "action": "OPEN_POSITION|ADD_POSITION|REDUCE_POSITION|CLOSE_POSITION|HOLD",
      "suggested_weight": 0.0,
      "rationale": "",
      "reflection_used": ""
    }
  ]
}
""".strip()

        payload = {
            "mode": mode,
            "market_regime": market_regime,
            "analysis_reports": analysis_reports,
            "reflections": reflections,
            "current_holdings": current_holdings,
            "retrieval_query_hint": {
                "company": state.get("company_of_interest", ""),
                "trade_date": state.get("trade_date", ""),
                "market_regime": market_regime,
            },
        }

        try:
            content = _run_with_tools(
                llm,
                system_prompt,
                json.dumps(payload, ensure_ascii=False),
                tools,
                run_id,
                "Portfolio Manager",
            )
            decision = _safe_json(content)
        except Exception as exc:
            if mode == "BATCH":
                decision = {
                    "portfolio_decisions": [
                        {
                            "ticker": state.get("company_of_interest", "UNKNOWN"),
                            "action": "HOLD",
                            "suggested_weight": 0.0,
                            "rationale": f"Fallback decision due to runtime issue: {exc}",
                            "reflection_used": "None",
                        }
                    ]
                }
            else:
                decision = {
                    "ticker": state.get("company_of_interest", "UNKNOWN"),
                    "final_action": "Hold",
                    "confidence_score": 50,
                    "market_regime_adjustment": "No adjustment",
                    "reflection_applied": "None",
                    "reasoning_summary": f"Fallback decision due to runtime issue: {exc}",
                    "risk_alert": "資料不足，需人工覆核",
                }

        AgentExecutionLogger.log_event(run_id, "node_output", "Portfolio Manager", {"decision": decision})
        return {
            "portfolio_decision": decision,
            "investment_plan": json.dumps(decision, ensure_ascii=False),
            "trader_investment_plan": json.dumps(decision, ensure_ascii=False),
            "final_trade_decision": json.dumps(decision, ensure_ascii=False),
        }

    return portfolio_manager_node
