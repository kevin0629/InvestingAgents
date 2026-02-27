"""
Technical Analyst subgraph (test version).

create_technical_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
每個 task 是一個獨立的 TechnicalState，透過 Send API 被呼叫。
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    TechnicalAnalysisReport,
    TechnicalVerificationReport,
    TechnicalOutput,
    Task,
)
from tradingagents.agents.utils.agent_utils import get_stock_data
from tradingagents.agents.utils.graph_helpers import clear_messages, handle_image_tool_results
from tradingagents.agents.utils.agent_states import TechnicalState




def create_technical_analyst(llm):
    """回傳 Technical Analyst 的 compiled subgraph。"""
    def _tool_name(tool):
        return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))

    tools = [
        get_stock_data,
        TechnicalOutput,
    ]

    def technical_analyst_node(state: TechnicalState):
        task = state["task"]
        end_date = state["end_date"]
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位技術分析師，主要任務是{task}，"
                    "次要任務是分析 {symbol} 的價格、成交量與技術指標，並判讀未來的走勢。\n"
                    "【資料截止日期】本次分析截止日期為 {end_date}。"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，"
                    "絕對不得使用超過此日期的任何價格或技術指標資料。\n"
                    "你可以使用下列工具: {tool_names}\n\n"
                    "任務指引: task_type 為 {task_type}。"
                    "若 task_type 是 VERIFICATION，代表這是庫存股，"
                    "你必須先驗證購買理由「{buy_reason}」有沒有符合預期，"
                    "並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有或加碼減碼。\n\n"
                    "在分析 {symbol} 的技術面時，請從以下層面全面評估：\n"
                    "1. 趨勢與價位分析: 判斷長期/中期/短期趨勢（上升/下降/盤整），指出關鍵支撐與壓力區間\n"
                    "2. 技術指標分析:\n"
                    "   - 移動平均線: 20MA / 60MA / 240MA 排列，判斷多頭或空頭排列\n"
                    "   - RSI: 超買(>70) / 超賣(<30)，注意頂/底背離\n"
                    "   - MACD: 快慢線交叉與柱狀體變化，判斷動能增減\n"
                    "   - 布林通道: 帶寬收斂/擴張，股價與上中下軌互動\n"
                    "3. 型態與成交量分析: 識別頭肩頂/底、W底/M頭、旗形、三角收斂等型態；分析成交量配合度（價漲量縮需警示）\n\n"
                    "交易建議標準:\n"
                    "- strong_buy: 長中短期皆多頭，RSI 無頂部背離，成交量配合\n"
                    "- buy: 長期多頭，中期多頭，短線回測支撐有守\n"
                    "- neutral: 長中短趨勢不一致，或布林帶收縮\n"
                    "- sell: 長期空頭，中期反彈無力\n"
                    "- strong_sell: 長中短期皆空頭，RSI 無底部背離，成交量配合價跌\n\n"
                    "完成分析後，請使用 TechnicalOutput 工具輸出結構化結果。"
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

    def _route(state: TechnicalState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "TechnicalOutput":
            return "technical_format"
        else:
            return "technical_tools"

    def _format_node(state: TechnicalState):
        last_msg = state["messages"][-1]
        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "TechnicalOutput":
                args = tc["args"]
                analysis     = [TechnicalAnalysisReport(**r)     for r in (args.get("technical_analysis_reports")     or [])]
                verification = [TechnicalVerificationReport(**r) for r in (args.get("technical_verification_reports") or [])]
                return {
                    "technical_analysis_reports":     analysis,
                    "technical_verification_reports": verification,
                }
        return {"technical_analysis_reports": [], "technical_verification_reports": []}

    sg = StateGraph(TechnicalState)
    sg.add_node("technical_clear",         clear_messages)
    sg.add_node("technical_llm",           technical_analyst_node)
    sg.add_node("technical_tools",         ToolNode(tools))  # only real tools
    sg.add_node("technical_image_handler", handle_image_tool_results)
    sg.add_node("technical_format",        _format_node)

    sg.add_edge(START, "technical_clear")
    sg.add_edge("technical_clear", "technical_llm")
    sg.add_conditional_edges("technical_llm", _route, ["technical_tools", "technical_format"])
    sg.add_edge("technical_tools", "technical_image_handler")
    sg.add_edge("technical_image_handler", "technical_llm")
    sg.add_edge("technical_format", END)

    return sg.compile()
