"""
Macro Analyst subgraph (test version).

create_macro_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
透過 Send API 以 end_date 啟動，專注於市場與宏觀環境分析。
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import MacroAnalysisReport
from tradingagents.agents.utils.agent_utils import (
    get_tools,
    get_taiex_data,
    search_news
)
from tradingagents.agents.utils.graph_helpers import clear_messages
from tradingagents.agents.utils.agent_states import MacroState



def create_macro_analyst(llm):
    """回傳 Macro Analyst 的 compiled subgraph。"""
    tools = [
        get_taiex_data,
        # search_news,
        MacroAnalysisReport,
    ]
    tool_names = get_tools(tools)

    def macro_analyst_node(state: MacroState):
        end_date = state["end_date"]
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位宏觀分析師，專注於市場層級的趨勢判讀與風險辨識。\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，嚴禁使用截止日期以後的資料。\n"
                    "你可以使用下列工具: {tool_names}\n\n"
                    "先使用 get_taiex_data 評估大盤趨勢，再使用 search_news 補充總經、政策、產業面催化與風險。\n"
                    "search_news 應使用市場層級查詢，避免個股導向，例如：\n"
                    "- 台灣央行 利率 政策\n"
                    "- 美國 CPI 聯準會 降息\n"
                    "- 半導體 景氣 循環 庫存\n"
                    "- 台股 外資 期貨 匯率\n\n"
                    "請在報告中至少涵蓋：\n"
                    "1. 市場趨勢與風險偏好（多頭/震盪/空頭）。\n"
                    "2. 關鍵宏觀驅動（利率、通膨、匯率、流動性、政策）。\n"
                    "3. 未來 1-4 週的主要上行與下行風險。\n"
                    "4. 對投資組合層級的操作建議（加減碼節奏、風險控管）。\n\n"
                    "評等標準：\n"
                    "- strong_buy: 風險偏好明顯改善，且宏觀驅動普遍偏多。\n"
                    "- buy: 整體環境偏多但仍有可控風險。\n"
                    "- neutral: 多空訊號混雜，建議中性配置。\n"
                    "- sell: 宏觀逆風升溫，建議降低風險曝險。\n"
                    "- strong_sell: 系統性風險升高，建議明顯防禦。\n\n"
                    "完成分析後，請使用 MacroAnalysisReport 工具輸出結構化結果。"
                    ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(end_date=end_date)
        prompt = prompt.partial(tool_names=tool_names)

        chain = prompt | llm.bind_tools(tools, tool_choice="any") # tool_choice="any" 時就無法同時使用會回傳圖片、文字的 tool，使用的話會導致 LLM 在看到末尾的 HumanMessage（攜帶圖片）後強制再呼叫工具而進入無限循環；

        return {"messages": [chain.invoke(state["messages"])]}


    def _route(state: MacroState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "MacroAnalysisReport":
            return "macro_format"
        else:
            return "macro_tools"

    def _format_node(state: MacroState):
        last_msg = state["messages"][-1]
        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "MacroAnalysisReport":
                return {"macro_analysis_report": tc["args"]}
        return {"macro_analysis_report": None}

    sg = StateGraph(MacroState)
    sg.add_node("macro_clear",  clear_messages)
    sg.add_node("macro_llm",    macro_analyst_node)
    sg.add_node("macro_tools",  ToolNode(tools))  # only real tools
    sg.add_node("macro_format", _format_node)

    sg.add_edge(START, "macro_clear")
    sg.add_edge("macro_clear", "macro_llm")
    sg.add_conditional_edges("macro_llm", _route, ["macro_tools", "macro_format"])
    sg.add_edge("macro_tools", "macro_llm")
    sg.add_edge("macro_format", END)

    return sg.compile()
