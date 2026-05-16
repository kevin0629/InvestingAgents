"""
Technical Analyst subgraph (test version).

create_technical_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
每個 task 是一個獨立的 TechnicalState，透過 Send API 被呼叫。
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    TechnicalAnalysisReport,
    TechnicalVerificationReport,
    TechnicalOutput,
    Task,
)
from tradingagents.agents.utils.agent_utils import (
    get_tools, 
    clear_messages,
    handle_image_tool_results,
    get_stock_data,
)
from tradingagents.agents.utils.agent_states import TechnicalState




def create_technical_analyst(llm):
    """回傳 Technical Analyst 的 compiled subgraph。"""
    tools = [
        get_stock_data,
        TechnicalOutput,
    ]

    tool_names = get_tools(tools)

    def technical_analyst_node(state: TechnicalState):
        task = state["task"]
        if isinstance(task, dict):
            task = Task(**task)
        end_date = state["end_date"]
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位專業且嚴謹的技術分析師，專注於透過價格行為、成交量與技術指標，判斷市場趨勢、動能變化與潛在轉折點。\n"
                    "你的分析將提供給 Portfolio Manager 參考，請務必盡可能詳細地提供信息，並附上具體、可操作的見解和佐證，幫助 Portfolio Manager 做出明智的決策。\n"
                    "如果你無法完全回答，沒關係；另一位助手會使用不同的工具來幫助你繼續完成未完成的工作。請盡你所能，努力取得進展。\n"
                    "目標：專注於尋找長線底部成型、超跌背離或價值浮現的打底標的。在嚴控下行風險下，追求穩健績效並優先發掘價格低估且具備防禦性支撐的公司，以期獲得長期穩定報酬。\n"
                    "交易規則：交易頻率為每月一次。不執行分批建倉、減倉、停損或停利等交易設定。\n"
                    "你的核心目標是：\n"
                    "1. 判斷 {symbol} 的趨勢方向（長期 / 中期 / 短期）\n"
                    "2. 評估市場動能與強弱\n"
                    "3. 識別關鍵支撐與壓力區\n"
                    "4. 給出具體交易建議（進場 / 減碼 / 觀望）"
                    "你的分析必須遵循以下原則：\n"
                    "- 採用「趨勢 → 動能 → 型態 → 成交量」分析順序\n"
                    "- 若技術指標出現衝突（如多頭排列但 RSI 背離），必須明確指出\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，"
                    "絕對不得使用超過此日期的任何資料。\n\n"
                    "你可以使用下列工具: {tool_names}\n\n"
                    "任務指引: task_type 為 {task_type}."
                    "若 task_type 是 ANALYSIS，代表這是新標的研究。"
                    "若 task_type 為 VERIFICATION（庫存股）或 HYBRID（連續被選中），請驗證購買理由「{buy_reason}」是否符合預期並偵測盲點："
                    "若為 VERIFICATION，輸出 technical_verification_reports，且 selected 必須為 false；若為 HYBRID，輸出 technical_verification_reports，且 selected 必須為 true。\n\n"
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
                    "嚴格輸出規則（必須遵守）:\n"
                    "- 每次只能輸出一種報告：`technical_analysis_reports` 或 `technical_verification_reports`，不可同時填寫兩者。\n"
                    "- `task_type=ANALYSIS`：只能輸出 `technical_analysis_reports`，且僅 1 筆。\n"
                    "- `task_type=VERIFICATION` 或 `task_type=HYBRID`：只能輸出 `technical_verification_reports`，且僅 1 筆。"
                    ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            symbol=task.symbol,
            end_date=end_date,
            task_type=task.task_type,
            buy_reason=task.buy_reason if task.task_type in {"VERIFICATION", "HYBRID"} else "N/A",
        )
        prompt = prompt.partial(tool_names=tool_names)

        chain = prompt | llm.bind_tools(tools, tool_choice="any") # tool_choice="any" 時就無法同時使用會回傳圖片、文字的 tool，使用的話會導致 LLM 在看到末尾的 HumanMessage（攜帶圖片）後強制再呼叫工具而進入無限循環；

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
        task = state.get("task")
        task_type = str((task or {}).get("task_type") if isinstance(task, dict) else getattr(task, "task_type", "ANALYSIS"))

        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "TechnicalOutput":
                args = tc["args"]
                analysis     = [TechnicalAnalysisReport(**r)     for r in (args.get("technical_analysis_reports")     or [])]
                verification = [TechnicalVerificationReport(**r) for r in (args.get("technical_verification_reports") or [])]

                if task_type in {"VERIFICATION", "HYBRID"}:
                    analysis = []
                    verification = verification[:1]
                    forced_selected = task_type == "HYBRID"
                    verification = [
                        report.model_copy(update={"selected": forced_selected})
                        for report in verification
                    ]
                else:
                    verification = []
                    analysis = analysis[:1]

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
