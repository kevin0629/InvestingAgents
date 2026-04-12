"""
News Analyst subgraph (test version).

create_news_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
每個 task 是一個獨立的 NewsState，透過 Send API 被呼叫。
"""

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    NewsAnalysisReport,
    NewsVerificationReport,
    NewsOutput,
    Task,
)
from tradingagents.agents.utils.agent_utils import (
    get_tools,
    clear_messages,
    get_company_news,
)
from tradingagents.agents.utils.agent_states import NewsState



def create_news_analyst(llm):
    """回傳 News Analyst 的 compiled subgraph。"""
    tools = [
        get_company_news,
        NewsOutput,
    ]

    tool_names = get_tools(tools)

    def news_analyst_node(state: NewsState):
        task = state["task"]
        if isinstance(task, dict):
            task = Task(**task)
        end_date = state["end_date"]
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位專業且嚴謹的新聞分析師，專注於從新聞事件中提煉出影響股價的關鍵催化劑，並將其轉化為可判斷股價影響的投資訊號。\n"
                    "你的分析將提供給 Portfolio Manager 參考，請務必盡可能詳細地提供信息，並附上具體、可操作的見解和佐證，幫助 Portfolio Manager 做出明智的決策。\n"
                    "如果你無法完全回答，沒關係；另一位助手會使用不同的工具來幫助你繼續完成未完成的工作。請盡你所能，努力取得進展。\n"
                    "交易規則：交易頻率為每月一次。不執行分批建倉、減倉、停損或停利等交易設定。\n"
                    "你的核心目標是：\n"
                    "1. 從新聞中識別對 {symbol} 有影響的關鍵事件\n"
                    "2. 判斷事件對公司的影響方向（正面 / 負面 / 中性）\n"
                    "3. 評估影響的時間範圍（短期 / 中期 / 長期）\n"
                    "4. 最終轉化為投資建議\n\n"
                    "你的分析必須遵循以下原則：\n"
                    "- 採用事件驅動分析方法，先辨識事件，分類事件，再評估影響，最後輸出投資判斷\n"
                    "- 僅保留對股價有實質影響的資訊，忽略雜訊新聞\n"
                    "- 每個結論必須對應具體新聞事件\n"
                    "- 若不同新聞產生矛盾訊號，必須明確指出\n\n"
                    "{company_info}\n\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，"
                    "絕對不得使用超過此日期的任何資料。\n\n"
                    "你可以使用下列工具: {tool_names}\n\n"
                    "任務指引: task_type 為 {task_type}."
                    "若 task_type 是 ANALYSIS，代表這是新標的研究，使用 `get_company_news` 工具時，look_back_days 務必設定為 None。而若是 VERIFICATION 或 HYBRID，look_back_days 務必設定為 30。\n"
                    "若 task_type 為 VERIFICATION（庫存股）或 HYBRID（連續被選中），請驗證購買理由「{buy_reason}」是否符合預期並偵測盲點："
                    "若為 VERIFICATION，輸出 news_verification_reports，且 selected 必須為 false；若為 HYBRID，輸出 news_verification_reports，且 selected 必須為 true。\n\n"
                    "投資建議標準:\n"
                    "- strong_buy: 事件顯著提升長期競爭力或護城河\n"
                    "- buy: 有成長催化，但存在短期不確定性\n"
                    "- neutral: 事件影響有限或市場已反應\n"
                    "- sell: 潛在風險增加或策略不確定\n"
                    "- strong_sell: 重大負面事件或決策錯誤\n\n"
                    "完成分析後，請使用 NewsOutput 工具輸出結構化結果。"
                    "嚴格輸出規則（必須遵守）:\n"
                    "- 每次只能輸出一種報告：`news_analysis_reports` 或 `news_verification_reports`，不可同時填寫兩者。\n"
                    "- `task_type=ANALYSIS`：只能輸出 `news_analysis_reports`，且僅 1 筆。\n"
                    "- `task_type=VERIFICATION` 或 `task_type=HYBRID`：只能輸出 `news_verification_reports`，且僅 1 筆。"
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

        chain = prompt | llm.bind_tools(tools, tool_choice="any") # tool_choice="any" 時就無法同時使用會回傳圖片、文字的 tool，使用的話會導致 LLM 在看到末尾的 HumanMessage（攜帶圖片）後強制再呼叫工具而進入無限循環；

        return {"messages": [chain.invoke(state["messages"])]}


    def _route(state: NewsState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "NewsOutput":
            return "news_format"
        else:
            return "news_tools"

    def _format_node(state: NewsState):
        last_msg = state["messages"][-1]
        task = state.get("task")
        task_type = str((task or {}).get("task_type") if isinstance(task, dict) else getattr(task, "task_type", "ANALYSIS"))

        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "NewsOutput":
                args = tc["args"]
                analysis     = [NewsAnalysisReport(**r)     for r in (args.get("news_analysis_reports")     or [])]
                verification = [NewsVerificationReport(**r) for r in (args.get("news_verification_reports") or [])]

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
                    "news_analysis_reports":     analysis,
                    "news_verification_reports": verification,
                }
        return {"news_analysis_reports": [], "news_verification_reports": []}

    sg = StateGraph(NewsState)
    sg.add_node("news_clear",  clear_messages)
    sg.add_node("news_llm",    news_analyst_node)
    sg.add_node("news_tools",  ToolNode(tools))  # only real tools
    sg.add_node("news_format", _format_node)

    sg.add_edge(START, "news_clear")
    sg.add_edge("news_clear", "news_llm")
    sg.add_conditional_edges("news_llm", _route, ["news_tools", "news_format"])
    sg.add_edge("news_tools", "news_llm")
    sg.add_edge("news_format", END)

    return sg.compile()
