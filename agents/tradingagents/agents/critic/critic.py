import json
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger
from tradingagents.agents.utils.agent_utils import retrieve_reflections, store_reflection


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
    max_steps: int = 6,
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
