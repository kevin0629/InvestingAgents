"""
News Analyst subgraph (test version).

create_news_analyst(llm) 回傳一個已 compile 的 StateGraph subgraph。
每個 task 是一個獨立的 NewsState，透過 Send API 被呼叫。
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    NewsAnalysisReport,
    NewsVerificationReport,
    NewsOutput,
    Task,
)
from tradingagents.agents.utils.agent_utils import get_company_info, search_news
from tradingagents.agents.utils.graph_helpers import clear_messages
from tradingagents.agents.utils.agent_states import NewsState



def create_news_analyst(llm):
    """回傳 News Analyst 的 compiled subgraph。"""
    def _tool_name(tool):
        return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))


    tools = [
        get_company_info,
        search_news,
        NewsOutput,
    ]

    def news_analyst_node(state: NewsState):
        task = state["task"]
        end_date = state["end_date"]
        
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位新聞分析師，主要任務是 {task}，"
                    "你的專長是從紛雜的新聞資訊中，提煉出對 {symbol} 股價有實質影響的催化劑。"
                    "你負責分析非結構化的文字資訊（擴廠、新產能、新技術、新產品、產業趨勢、供應鏈等），"
                    "並將其轉化為對未來股價的影響力評估。\n"
                    "【資料截止日期】本次分析截止日期為 {end_date}。"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，"
                    "絕對不得使用超過此日期的任何資料。\n\n"
                    "你可以使用下列工具: {tool_names}\n\n"
                    "每次呼叫 search_news 的 query 格式：「{symbol} + 具體業務關鍵字」。\n"
                    "例如：「{symbol} 擴廠計畫」、「{symbol} 新客戶訂單」、"
                    "「{symbol} 供應鏈缺貨」、「{symbol} 併購案」。\n\n"
                    "任務指引: task_type 為 {task_type}。"
                    "若 task_type 是 VERIFICATION，代表這是庫存股，"
                    "你必須先驗證購買理由「{buy_reason}」有沒有符合預期，"
                    "並偵測盲點，確認沒有忽略其他狀況。\n\n"
                    "分析方向（依事件類型）：\n"
                    "- 擴張事件（併購/擴產）: 戰略意圖、未來 1-3 年對 EPS 的影響、護城河是否增強、潛在風險\n"
                    "- 新產品/技術: 破壞式/持續性/漸進式創新判斷、解決的核心痛點、TAM/SAM/SOM 規模\n"
                    "- 產業趨勢: 趨勢定義與發展階段（萌芽/成長/成熟/衰退）、對產業價值鏈的重塑、利潤最集中環節\n"
                    "- 供應鏈狀況: 訂單/供應商/需求變動、影響時間範圍（短期/中期/長期）\n\n"
                    "投資建議標準:\n"
                    "- strong_buy: 擴張能顯著增強護城河或取得關鍵技術，且資金充裕\n"
                    "- buy: 雖擴大市佔，但短期面臨整合陣痛或股權稀釋，回檔是長線佈局點\n"
                    "- neutral: 影響有限，屬維持競爭力的例行支出，市場通常已反應\n"
                    "- sell: 轉型豪賭（跨界整合/高槓桿），成敗未定，建議等待財報驗證\n"
                    "- strong_sell: 溢價收購或無助核心競爭力，不利股東\n\n"
                    "完成分析後，請使用 NewsOutput 工具輸出結構化結果。"
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


    def _route(state: NewsState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "NewsOutput":
            return "news_format"
        else:
            return "news_tools"

    def _format_node(state: NewsState):
        last_msg = state["messages"][-1]
        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "NewsOutput":
                args = tc["args"]
                analysis     = [NewsAnalysisReport(**r)     for r in (args.get("news_analysis_reports")     or [])]
                verification = [NewsVerificationReport(**r) for r in (args.get("news_verification_reports") or [])]
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
