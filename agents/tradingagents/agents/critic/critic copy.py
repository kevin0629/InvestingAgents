import json
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger
from tradingagents.agents.utils.agent_utils import retrieve_reflections, store_reflection



def create_critic(llm):
    def critic_node(state):
        run_id = state.get("run_id", "")
        AgentExecutionLogger.log_event(run_id, "node_start", "Critic", {"coordinator_plan": state.get("coordinator_plan", {})})
        tools = [retrieve_reflections, store_reflection]
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
你有兩個可用工具：
1) retrieve_reflections：先檢索歷史反思
2) store_reflection：產出結論後再儲存你的新反思

每個任務都必須先呼叫 retrieve_reflections，再呼叫 store_reflection，最後只輸出上述 JSON。
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
                content = _run_with_tools(
                    llm,
                    system_prompt,
                    json.dumps(payload, ensure_ascii=False),
                    tools,
                    run_id,
                    "Critic",
                )
                parsed = _safe_json(content)
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

        return {"critic_reflections": reflections}

    return critic_node
