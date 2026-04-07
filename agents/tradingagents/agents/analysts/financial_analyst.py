"""
Financial Analyst subgraph (test version).

create_financial_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
每個 task 是一個獨立的 FinancialState，透過 Send API 被呼叫。
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_output_formats import (
    FinancialAnalysisReport,
    FinancialVerificationReport,
    Task,
    FinancialOutput
)
from tradingagents.agents.utils.agent_utils import (
    get_tools,
    get_balance_sheet,
    get_cashflow,
    get_dupont_analysis,
    get_factors,
    get_income_statement,
    get_monthly_revenue,
    get_river_chart,
)
from tradingagents.agents.utils.graph_helpers import clear_messages, handle_image_tool_results
from tradingagents.agents.utils.agent_states import FinancialState



def create_financial_analyst(llm):
    """回傳 Financial Analyst 的 compiled subgraph。"""
    tools = [
        get_balance_sheet,
        get_cashflow,
        get_dupont_analysis,
        get_factors,
        get_income_statement,
        get_monthly_revenue,
        get_river_chart,
        FinancialOutput,
    ]
    tool_names = get_tools(tools)

    def financial_analyst_node(state: FinancialState):
        task = state["task"]
        if isinstance(task, dict):
            task = Task(**task)
        end_date = state["end_date"]

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位專業且嚴謹的財務分析師，具備多年市場經驗，專注於從基本面數據中挖掘公司真實價值，並提供具備可執行性的投資判斷。\n"
                    "你的分析將直接影響投資決策，因此必須確保結論具備高度可靠性與一致性。\n"
                    "你的核心目標是：\n"
                    "1. 判斷 {symbol} 目前估值是否合理（低估 / 高估）\n"
                    "2. 評估未來基本面是否支持股價上升\n"
                    "3. 最終給出具體投資建議\n\n"
                    "你的分析必須遵循以下原則：\n"
                    "- 採用 bottom-up 的分析方法，先分析財務數據，再推導公司體質和成長性，最後評估股價表現\n"
                    "- 所有結論必須基於具體財務數據\n"
                    "- 若數據出現矛盾，必須明確指出\n"
                    "{symbol} 的基本資料：\n"
                    "{company_info}\n\n"
                    "你可以使用的工具: {tool_names}\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，嚴禁使用截止日期以後的資料。\n"
                    "分析步驟:\n"
                    "Step1: task_type 為 {task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證 {buy_reason} 有沒有符合預期，並偵測盲點。\n"
                    "若 `task_type` 是 HYBRID，代表這支股票上期與本期都被選到，你必須"
                    "針對既有 buy_reason 的驗證（輸出到 financial_verification_reports，並將 selected 設為 true）\n\n"
                    "判斷標準範例:\n"
                    "- SUCCESS: 數據完全支持當初的論點（例如：預測毛利升，真的升了）\n"
                    "- FAILURE: 數據與預測相反（例如：預測營收增，結果持平或衰退）\n"
                    "- NEUTRAL: 無法判斷或雜訊過多\n\n"
                    "Step2: 三大報表分析、財務指標分析、杜邦分析、河流圖分析等工具，從財務面分析 {symbol} 的表現，並評估未來股價上升的可能性。請具體分析財務數據，並給出結論。\n"
                    "1. 三大報表分析:\n"
                    "- 損益表: 分析近期的營收、毛利、營業利益及淨利，判斷公司的成長趨勢\n   "
                    "- 資產負債表: 分析公司的資產結構、負債結構及股東權益，評估公司的財務穩健程度\n"
                    "- 現金流量表: 分析公司的營運現金流、投資現金流及融資現金流，評估公司的現金流狀況\n"
                    "2. 財務指標分析:\n"
                    "- 獲利能力指標: 如毛利率、營業利益率、淨利率等，評估公司的獲利能力\n"
                    "- 償債能力指標: 如流動比率、負債比率等，評估公司的償債能力\n"
                    "- 經營效率指標: 如存貨週轉天數、應收帳款週轉天數等，評估公司的經營效率\n"
                    "3. 杜邦分析:\n"
                    "- 分析公司的ROE，並拆解成淨利率、資產週轉率和財務槓桿，評估公司的盈利能力和經營效率\n"
                    "4. 河流圖分析:\n"
                    "- 分析公司目前的本益比位於歷史區間的相對高點、低點或平均水平？ 分析本益比的變動，是否與公司 EPS 增長的趨勢相匹配\n\n"
                    "列出具體的財務風險，例如：應收帳款異常增加\n"
                    "你的所有結論都必須基於嚴謹的財務數據與量化證據，並保持客觀中立的判斷，給出投資建議:\n"
                    "- strong_buy: 基本面強 + 明顯低估\n"
                    "- buy: 基本面穩 + 合理價格\n"
                    "- neutral: 市場已反映預期\n"
                    "- sell: 基本面轉弱或高估\n"
                    "- strong_sell: 基本面惡化 + 財務警訊\n"
                    "完成分析後，請使用 FinancialOutput 工具輸出結構化結果，此工具只能使用一次，每次使用請確保輸入的資訊完整。"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            symbol=task.symbol,
            end_date=end_date,
            task_type=task.task_type,
            company_info=task.company_info,
            buy_reason=task.buy_reason if task.task_type in {"VERIFICATION", "HYBRID"} else "N/A",
        )
        prompt = prompt.partial(tool_names=tool_names)

        chain = prompt | llm.bind_tools(tools)   # tool_choice="any" 時就無法同時使用會回傳圖片、文字的 tool，使用的話會導致 LLM 在看到末尾的 HumanMessage（攜帶圖片）後強制再呼叫工具而進入無限循環；

        return {"messages": [chain.invoke(state["messages"])]}


    def _route(state: FinancialState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "FinancialOutput":
            return "financial_format"
        else:
            return "financial_tools"

    def _format_node(state: FinancialState):
        last_msg = state["messages"][-1]
        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "FinancialOutput":
                args = tc["args"]
                analysis     = [FinancialAnalysisReport(**r)     for r in (args.get("financial_analysis_reports")     or [])]
                verification = [FinancialVerificationReport(**r) for r in (args.get("financial_verification_reports") or [])]
                return {
                    "financial_analysis_reports":     analysis,
                    "financial_verification_reports": verification,
                }
        return {"financial_analysis_reports": [], "financial_verification_reports": []}

    sg = StateGraph(FinancialState)
    sg.add_node("financial_clear", clear_messages)          # 隔離父 graph 的 messages
    sg.add_node("financial_llm", financial_analyst_node)
    sg.add_node("financial_tools", ToolNode(tools))
    sg.add_node("financial_image_handler", handle_image_tool_results)
    sg.add_node("financial_format", _format_node)

    sg.add_edge(START, "financial_clear")
    sg.add_edge("financial_clear", "financial_llm")
    sg.add_conditional_edges("financial_llm", _route, ["financial_tools", "financial_format"])
    sg.add_edge("financial_tools", "financial_image_handler")
    sg.add_edge("financial_image_handler", "financial_llm")
    sg.add_edge("financial_format", END)

    return sg.compile()
