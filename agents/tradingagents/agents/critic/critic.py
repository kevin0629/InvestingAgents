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


def create_critic(llm, memory=None):
    def critic_node(state):
        run_id = state.get("run_id", "")
        AgentExecutionLogger.log_event(run_id, "node_start", "Critic", {"coordinator_plan": state.get("coordinator_plan", {})})
        plan = state.get("coordinator_plan", {})
        verification_tasks = [
            task for task in plan.get("tasks", []) if task.get("task_type") == "VERIFICATION"
        ]
        if not verification_tasks:
            return {"critic_reflections": []}

        financial_by_ticker = {
            item.get("ticker"): item.get("report", {}) for item in state.get("financial_reports", [])
        }
        technical_by_ticker = {
            item.get("ticker"): item.get("report", {}) for item in state.get("technical_reports", [])
        }
        news_by_ticker = {
            item.get("ticker"): item.get("report", {}) for item in state.get("news_reports", [])
        }

        system_prompt = """
你是 Critic Agent。必須輸出 JSON：
{
  "ticker": "",
  "validation_status": "SUCCESS|FAILURE|NEUTRAL",
  "root_cause_category": "Logic Error|Data Error|Market Sentiment|Metric Misjudgment",
  "analysis": "",
  "bias_detected": "",
  "lesson_learned": ""
}
必須基於 verification reports 的具體內容，不可泛化。
""".strip()

        reflections = []
        for task in verification_tasks:
            ticker = task.get("ticker")
            payload = {
                "ticker": ticker,
                "original_thesis": task.get("context", ""),
                "actual_outcome": task.get("actual_outcome", ""),
                "verification_reports": {
                    "financial": financial_by_ticker.get(ticker),
                    "technical": technical_by_ticker.get(ticker),
                    "news": news_by_ticker.get(ticker),
                },
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
                    "Critic",
                    {
                        "ticker": ticker,
                        "content": response.content,
                        "reasoning_trace": getattr(response, "reasoning_content", None)
                        or getattr(response, "additional_kwargs", {}).get("reasoning"),
                    },
                )
                parsed = _safe_json(response.content)
            except Exception as exc:
                parsed = {
                    "ticker": ticker,
                    "validation_status": "NEUTRAL",
                    "root_cause_category": "Data Error",
                    "analysis": f"Critic fallback due to parsing/runtime issue: {exc}",
                    "bias_detected": "Unknown",
                    "lesson_learned": "資料不足時，暫停加碼並等待下一期驗證資料。",
                }

            reflections.append(parsed)
            AgentExecutionLogger.log_event(run_id, "node_output", "Critic", {"ticker": ticker, "reflection": parsed})
            if memory is not None:
                situation = json.dumps(payload, ensure_ascii=False)
                memory.add_situations([(situation, json.dumps(parsed, ensure_ascii=False))])

        return {"critic_reflections": reflections}

    return critic_node
