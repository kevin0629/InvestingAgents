from tradingagents.agents.utils.agent_output_formats import FinancialOutput
from langchain_core.messages import HumanMessage

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



def create_financial_analyst(llm):
    def financial_analyst_node(state) -> dict:
        def _extract_payload(result, output_tool_name):
            tool_calls = getattr(result, "tool_calls", None) or []
            for call in tool_calls:
                if call.get("name") == output_tool_name:
                    return call.get("args", {}) or {}
            content = getattr(result, "content", None)
            if isinstance(content, dict):
                return content
            return {}

        def _tool_name(tool):
            return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))

        data_tools = [
            get_balance_sheet,
            get_cashflow,
            get_company_info,
            get_dupont_analysis,
            get_factors,
            get_income_statement,
            get_monthly_revenue,
            get_river_chart,
        ]
        llm_tools = data_tools + [FinancialOutput]  # include output schema so LLM can terminate loop
        tool_names = ", ".join([_tool_name(tool) for tool in data_tools])

        def _get_value(payload, key, default=""):
            if payload is None:
                return default
            if isinstance(payload, dict):
                return payload.get(key, default)
            return getattr(payload, key, default)

        task_payload = state.get("financial_task")
        task_payloads = []
        if task_payload is not None:
            task_payloads = [task_payload]
        else:
            financial_tasks = state.get("financial_tasks") or []
            if isinstance(financial_tasks, list):
                task_payloads = financial_tasks
            elif isinstance(financial_tasks, dict):
                task_payloads = [financial_tasks]

        symbols = [str(_get_value(task, "symbol", "")) for task in task_payloads if _get_value(task, "symbol", "")]
        task_types = [str(_get_value(task, "task_type", "")) for task in task_payloads if _get_value(task, "task_type", "")]
        task_descriptions = [str(_get_value(task, "task", "")) for task in task_payloads if _get_value(task, "task", "")]
        buy_reasons = [str(_get_value(task, "buy_reason", "")) for task in task_payloads if _get_value(task, "buy_reason", "")]

        symbol = ", ".join(symbols)
        task_type = ", ".join(task_types)
        task = "\n".join([f"- {description}" for description in task_descriptions])
        buy_reason = "\n".join([f"- {reason}" for reason in buy_reasons])

        # --- DEBUG ---
        print(f"\n[Financial Analyst] received {len(task_payloads)} task(s)")
        print(f"  symbols   : {symbols}")
        print(f"  task_type : {task_type}")
        for _i, _t in enumerate(task_payloads):
            print(f"  task[{_i}]  : {_t}")
        print(f"  financial_messages so far: {len(state.get('financial_messages', []))}")

        if not symbols:
            print("[Financial Analyst] No valid symbols — skipping.")
            return {}

        prompt = f"""你是一位財務分析師，負責評估{symbol}股價是被低估還是被高估，並分析未來公司股價上升的可能性。\n
        你的任務為 {task}\n
        你可以使用下列工具取得額外資訊: {tool_names}\n
        你只能查詢以下股票代號的資料：{symbol}。
        絕對禁止查詢任何未在上方列出的股票代號（例如 UNKNOWN 或其他任何代號）。若工具呼叫的 symbol 參數不在 [{symbol}] 清單內，視為違規，請立即停止並改用正確代號。\n
        Step1: task_type 為 {task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證{buy_reason}有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有。\n
判斷標準範例: 
- SUCCESS: 數據完全支持當初的論點（例如：預測毛利升，真的升了）
- FAILURE: 數據與預測相反（例如：預測營收增，結果持平或衰退）
- NEUTRAL: 無法判斷或雜訊過多

Step2: 三大報表分析、財務指標分析、杜邦分析、河流圖分析等工具，從財務面分析{symbol}的表現，並評估未來股價上升的可能性。請具體分析財務數據，並給出結論。\n
1. 三大報表分析:\n
- 損益表: 分析近期的營收、毛利、營業利益及淨利，判斷公司的成長趨勢
- 資產負債表: 分析公司的資產結構、負債結構及股東權益，評估公司的財務穩健程度
- 現金流量表: 分析公司的營運現金流、投資現金流及融資現金流，評估公司的現金流狀況

2. 財務指標分析:\n
- 獲利能力指標: 如毛利率、營業利益率、淨利率等，評估公司的獲利能力
- 償債能力指標: 如流動比率、負債比率等，評估公司的償債能力
- 經營效率指標: 如存貨週轉天數、應收帳款週轉天數等，評估公司的經營效率

3. 杜邦分析:\n
- 分析公司的ROE，並拆解成淨利率、資產週轉率和財務槓桿，評估公司的盈利能力和經營效率

4. 河流圖分析:\n
- 分析公司目前的本益比位於歷史區間的相對高點、低點或平均水平？ 分析本益比的變動，是否與公司 EPS 增長的趨勢相匹配\n

列出具體的財務風險，例如：應收帳款異常增加\n
你的所有結論都必須基於嚴謹的財務數據與量化證據，並保持客觀中立的判斷，給出投資建議:\n
- strong_buy: 積極關注。公司基本面強勁且股價被錯殺，具有極高的安全邊際，適合長線投資人分批佈局。
- buy: 持有/續抱。公司在合理的價格，建議持有並關注營收成長動能是否延續。
- neutral: 謹慎持有。市場已給予高期待。股價對財報容錯率低，建議關注成長率是否放緩，不宜大舉追高。
- sell: 迴避/減碼。股價嚴重脫離基本面，風險極高，建議遠離或獲利了結。
- strong_sell: 觀望。嚴重脫離基本面，且出現財務警訊 (如現金流轉負)。
"""

        try:
            llm_with_tools = llm.bind_tools(llm_tools, tool_choice="any")
        except Exception:
            llm_with_tools = llm.bind_tools(llm_tools)

        messages = list(state.get("financial_messages", []))
        if not messages:
            messages = [HumanMessage(content=prompt)]
        result = llm_with_tools.invoke(messages)

        report = _extract_payload(result, FinancialOutput.__name__)
        analysis_reports = report.get("financial_analysis_reports", [])
        verification_reports = report.get("financial_verification_reports", [])

        output = {"financial_messages": [result]}
        if analysis_reports:
            output["financial_analysis_reports"] = analysis_reports
        if verification_reports:
            output["financial_verification_reports"] = verification_reports
        return output

    return financial_analyst_node
