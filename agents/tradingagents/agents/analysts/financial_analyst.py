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

        task = state["financial_tasks"]["task"]
        symbol = task["symbol"]
        task_type = task["task_type"]
        buy_reason = task["buy_reason"]
        task = task["task"]

        prompt = f"""你是一位財務分析師，負責評估{symbol}股價是被低估還是被高估，並分析未來公司股價上升的可能性。\n

        你可以使用下列工具取得額外資訊: {tool_names}\n
        Step1: task_type 為 {task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證{buy_reason}有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有。\n
判斷標準範例: 
- SUCCESS: 數據完全支持當初的論點（例如：預測毛利升，真的升了）
- FAILURE: 數據與預測相反（例如：預測營收增，結果持平或衰退）
- NEUTRAL: 無法判斷或雜訊過多

Step2: 三大報表分析、財務指標分析、杜邦分析、河流圖分析等工具，從財務面分析{symbol}的表現，並評估未來股價上升的可能性。請具體分析財務數據，並給出結論。\n

列出具體的財務風險，例如：應收帳款異常增加\n
你的所有結論都必須基於嚴謹的財務數據與量化證據，並保持客觀中立的判斷，給出投資建議:\n
- strong_buy: 積極關注。公司基本面強勁且股價被錯殺，具有極高的安全邊際，適合長線投資人分批佈局。
- buy: 持有/續抱。公司在合理的價格，建議持有並關注營收成長動能是否延續。
- neutral: 謹慎持有。市場已給予高期待。股價對財報容錯率低，建議關注成長率是否放緩，不宜大舉追高。
- sell: 迴避/減碼。股價嚴重脫離基本面，風險極高，建議遠離或獲利了結。
- strong_sell: 觀望。嚴重脫離基本面，且出現財務警訊 (如現金流轉負)。
"""

        structured_llm = llm.with_structured_output(FinancialOutput)
        structured_llm_with_tools = structured_llm.bind_tools(tools)

        result = structured_llm_with_tools.invoke(prompt)

        market_situation = ""
        end_date = ""
        
        strategy = ""
        technical_tasks = None
        fundamental_tasks = None
        news_tasks = None

        if len(result.tool_calls) == 0:
            market_situation = result.market_situation
            end_date = result.end_date
            strategy = result.strategy
            technical_tasks = result.technical_tasks
            fundamental_tasks = result.fundamental_tasks
            news_tasks = result.news_tasks

        return {
            "market_situation": market_situation,
            "end_date": end_date,
            "strategy": strategy,
            "technical_tasks": technical_tasks,
            "fundamental_tasks": fundamental_tasks,
            "news_tasks": news_tasks,
        }

    return financial_analyst_node
