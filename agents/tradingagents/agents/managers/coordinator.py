import json
from typing import Any, Dict, List


def _safe_json(content: str) -> Dict[str, Any]:
    text = (content or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        text = text[start:end + 1]
    return json.loads(text)


def _build_fallback_plan(user_request: str, trade_date: str) -> Dict[str, Any]:
    ticker = user_request.strip().split()[0].upper() if user_request.strip() else "2330"
    return {
        "mode": "single",
        "market_regime": "Neutral to Risk-Off",
        "tasks": [
            {
                "agent": "Financial_Analyst",
                "ticker": ticker,
                "task_type": "ANALYSIS",
                "end_time": trade_date,
                "instruction": "分析近一年營收、三率、現金流與估值位階。",
            },
            {
                "agent": "Technical_Analyst",
                "ticker": ticker,
                "task_type": "ANALYSIS",
                "end_time": trade_date,
                "instruction": "分析長中短趨勢、關鍵支撐壓力、RSI/MACD/布林與量價關係。",
            },
            {
                "agent": "News_Analyst",
                "ticker": ticker,
                "task_type": "ANALYSIS",
                "end_time": trade_date,
                "instruction": "分析近期擴張、產品技術、供應鏈與宏觀趨勢對股價影響。",
            },
        ],
    }


def create_coordinator(llm):
    def coordinator_node(state):
        user_request = state.get("user_request") or state.get("company_of_interest", "")
        trade_date = state.get("trade_date", "")

        system_prompt = """
你是金融研究協調員 Coordinator。
你必須且只能輸出 JSON，不要輸出任何額外文字。

請依下列規格輸出：
{
  "mode": "batch" | "single",
  "market_regime": "簡短市場情緒",
  "tasks": [
    {
      "agent": "Financial_Analyst" | "Technical_Analyst" | "News_Analyst",
      "ticker": "股票代碼",
      "task_type": "ANALYSIS" | "VERIFICATION",
      "start_time": "可選",
      "end_time": "可選",
      "instruction": "具體任務",
      "context": "可選，特別是 VERIFICATION 時放 past_rationale"
    }
  ]
}

規則：
1) 若使用者是單點查詢，mode=single，派發對應任務。
2) 若是月度再平衡，mode=batch，Candidates 做 ANALYSIS，Holdings 做 VERIFICATION。
3) instruction 必須具體可執行。
""".strip()

        try:
            response = llm.invoke([
                ("system", system_prompt),
                ("human", f"request={user_request}\ntrade_date={trade_date}"),
            ])
            plan = _safe_json(response.content)
            if not isinstance(plan, dict) or "tasks" not in plan:
                raise ValueError("invalid coordinator json")
        except Exception:
            plan = _build_fallback_plan(user_request, trade_date)

        mode = str(plan.get("mode", "single")).lower()
        return {
            "coordinator_plan": plan,
            "mode": mode,
            "market_regime": plan.get("market_regime", "Neutral"),
            "messages": [("ai", json.dumps(plan, ensure_ascii=False))],
        }

    return coordinator_node
