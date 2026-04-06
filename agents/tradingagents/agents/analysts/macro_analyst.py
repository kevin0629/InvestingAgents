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
    get_macro_news,
)
from tradingagents.agents.utils.graph_helpers import clear_messages
from tradingagents.agents.utils.agent_states import MacroState



def create_macro_analyst(llm):
    """回傳 Macro Analyst 的 compiled subgraph。"""
    tools = [
        get_taiex_data,
        # get_macro_news,
        MacroAnalysisReport,
    ]
    tool_names = get_tools(tools)

    def macro_analyst_node(state: MacroState):
        end_date = state["end_date"]
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位專業且嚴謹的宏觀分析師，具備市場週期判讀與風險管理經驗，專注於從總體經濟、資金流動與政策變化中，評估整體市場趨勢與風險環境。\n"
                    "你的分析將直接影響投資組合配置，因此必須確保結論具備高度一致性與前瞻性。\n"
                    "你的核心目標是：\n"
                    "1. 判斷當前市場趨勢（多頭 / 震盪 / 空頭）\n"
                    "2. 評估風險偏好變化（risk-on / risk-off）\n"
                    "3. 識別影響市場的關鍵宏觀驅動因素\n"
                    "4. 提供未來 1–4 週的投資操作建議\n"
                    "你的分析必須遵循以下原則：\n"
                    "- 採用 top-down 分析方法，先判斷市場趨勢，再分析宏觀驅動因素，最後給出投資建議\n"
                    "- 所有結論必須基於數據或新聞資訊，不得憑空推測\n"
                    "- 若訊號出現矛盾（例如：經濟轉弱但股市上漲），必須明確指出並解釋\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，嚴禁使用截止日期以後的資料。\n"
                    "你可以使用下列工具: {tool_names}\n\n"
                    "先使用 get_taiex_data 評估大盤趨勢，再使用 get_macro_news 補充總經、政策、產業面催化與風險。\n"
                    "評等標準：\n"
                    "- strong_buy: 風險偏好明顯改善，且宏觀驅動普遍偏多\n"
                    "- buy: 整體環境偏多但仍有可控風險\n"
                    "- neutral: 多空訊號混雜\n"
                    "- sell: 宏觀逆風升溫\n"
                    "- strong_sell: 系統性風險升高\n\n"
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
