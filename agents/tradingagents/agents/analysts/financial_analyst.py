from tradingagents.agents.utils.agent_output_formats import FinancialOutput

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
        tools = [
            get_balance_sheet,
            get_cashflow,
            get_company_info,
            get_dupont_analysis,
            get_factors,
            get_income_statement,
            get_monthly_revenue,
            get_river_chart,
        ]
        tool_names = ", ".join([tool.name for tool in tools])

        def _get_value(payload, key, default=""):
            if payload is None:
                return default
            if isinstance(payload, dict):
                return payload.get(key, default)
            return getattr(payload, key, default)

        task_payload = state.get("financial_task")
        if task_payload is None:
            financial_tasks = state.get("financial_tasks") or []
            if isinstance(financial_tasks, list) and financial_tasks:
                task_payload = financial_tasks[0]
            elif isinstance(financial_tasks, dict):
                task_payload = financial_tasks.get("task")

        symbol = _get_value(task_payload, "symbol", "")
        task_type = _get_value(task_payload, "task_type", "")
        buy_reason = _get_value(task_payload, "buy_reason", "")
        task = _get_value(task_payload, "task", "")

        prompt = f"""你是一位財務分析師，負責評估{symbol}股價是被低估還是被高估，並分析未來公司股價上升的可能性。\n
        你的任務為 {task}\n
        你可以使用下列工具取得額外資訊: {tool_names}\n
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
            llm_for_chain = llm.bind_tools(tools).with_structured_output(FinancialOutput)
        except Exception:
            llm_for_chain = llm.with_structured_output(FinancialOutput)

        result = llm_for_chain.invoke(prompt)

        analysis_reports = getattr(result, "financial_analysis_reports", None)
        verification_reports = getattr(result, "financial_verification_reports", None)

        if analysis_reports is not None:
            return {"financial_analysis_reports": analysis_reports}
        else:
            return {"financial_verification_reports": verification_reports}

    return financial_analyst_node
