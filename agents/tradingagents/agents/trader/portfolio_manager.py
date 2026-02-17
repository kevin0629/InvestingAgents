import json
from typing import Any, Dict
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger


def _safe_json(content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start:end + 1]
    return json.loads(text)


def create_portfolio_manager(llm):
    def portfolio_manager_node(state):
        run_id = state.get("run_id", "")
        mode = str(state.get("mode", "single")).upper()
        market_regime = state.get("market_regime", "Neutral")
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
        }

        try:
            response = llm.invoke(
                [
                    ("system", system_prompt),
                    ("human", json.dumps(payload, ensure_ascii=False)),
                ]
            )
            AgentExecutionLogger.log_event(
                run_id,
                "llm_output",
                "Portfolio Manager",
                {
                    "content": response.content,
                    "reasoning_trace": getattr(response, "reasoning_content", None)
                    or getattr(response, "additional_kwargs", {}).get("reasoning"),
                },
            )
            decision = _safe_json(response.content)
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
