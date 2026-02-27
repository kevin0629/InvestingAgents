"""
Financial Analyst subgraph (test version).

create_financial_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
每個 task 是一個獨立的 FinancialState，透過 Send API 被呼叫。
"""

import operator
from typing import Annotated, List
from typing_extensions import TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_output_formats import (
    FinancialAnalysisReport,
    FinancialVerificationReport,
    Task,
    FinancialOutput
)
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
from tradingagents.agents.utils.graph_helpers import clear_messages, handle_image_tool_results
from tradingagents.agents.utils.agent_states import FinancialState



def create_financial_analyst(llm):
    """回傳 Financial Analyst 的 compiled subgraph。"""
    def _tool_name(tool):
        return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))
    
    tools = [
        get_balance_sheet,
        get_cashflow,
        get_company_info,
        get_dupont_analysis,
        get_factors,
        get_income_statement,
        get_monthly_revenue,
        get_river_chart,
        FinancialOutput,
    ]

    def financial_analyst_node(state: FinancialState):
        task = state["task"]
        end_date = state["end_date"]

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位財務分析師，主要任務是{task}，次要任務要評估 {symbol} 股價是被低估還是被高估，並分析未來公司股價上升的可能性。\n"
                    "你可以使用的工具: {tool_names}\n"
                    "本次分析截止日期為 {end_date}，所有工具呼叫的 end_date 參數皆必須設為 {end_date}（或更早），嚴禁使用截止日期以後的資料。\n"
                    "分析步驟:\n"
                    "Step1: task_type 為 {task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證 {buy_reason} 有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有。\n"
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
                    "- strong_buy: 積極關注。公司基本面強勁且股價被錯殺，具有極高的安全邊際，適合長線投資人分批佈局\n"
                    "- buy: 持有/續抱。公司在合理的價格，建議持有並關注營收成長動能是否延續\n"
                    "- neutral: 謹慎持有。市場已給予高期待。股價對財報容錯率低，建議關注成長率是否放緩，不宜大舉追高\n"
                    "- sell: 迴避/減碼。股價嚴重脫離基本面，風險極高，建議遠離或獲利了結\n"
                    "- strong_sell: 觀望。嚴重脫離基本面，且出現財務警訊 (如現金流轉負)\n"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            task=task.task,
            symbol=task.symbol,
            end_date=end_date,
            task_type=task.task_type,
            buy_reason=task.buy_reason if task.task_type == "VERIFICATION" else "N/A",
        )
        prompt = prompt.partial(tool_names=", ".join([_tool_name(tool) for tool in tools]))

        chain = prompt | llm.bind_tools(tools, tool_choice="any")

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
