"""
Portfolio Manager subgraph (test version).

create_portfolio_manager(llm) 回傳一個已 compile 的 StateGraph subgraph。
Portfolio Manager 同時接收 AnalysisReport（新標的）與 VerificationReport（庫存股驗證），
以及 Critic 的反思教訓，最終輸出投資組合決策。
"""

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    PortfolioDecision,
    PortfolioDecisions,
)
from tradingagents.agents.utils.graph_helpers import clear_messages
from tradingagents.agents.utils.agent_states import PortfolioState
from tradingagents.agents.utils.agent_utils import get_tools



def create_portfolio_manager(llm):
    """回傳 Portfolio Manager 的 compiled subgraph。"""
    tools = [PortfolioDecisions]
    tool_names = get_tools(tools)

    def portfolio_manager_node(state: PortfolioState):
        # user_query = state.get("user_query", "No user query provided.")
        # mode = state.get("mode", "Unknown")
        end_date = state.get("end_date", "Unknown")
        # strategy = state.get("strategy", "Unknown")
        market_situation = state.get("market_situation", "Unknown")

        fin_analysis   = state.get("financial_analysis_reports") or []
        tech_analysis  = state.get("technical_analysis_reports") or []
        news_analysis  = state.get("news_analysis_reports") or []
        fin_verify     = state.get("financial_verification_reports") or []
        tech_verify    = state.get("technical_verification_reports") or []
        news_verify    = state.get("news_verification_reports") or []
        # critic_summary = "\n".join(state.get("critic_reflections") or [])

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是擁有最終裁量權的投資長。你的工作是做出投資決策。\n"
                    "你需要綜合考量分析師的報告、市場情況、歷史教訓，"
                    "目標是建構一個「高勝率」、「高報酬」且「風險可控」的投資組合。\n"
                    "當子 Agent 意見分歧時，由你進行最終裁決。\n\n"
                    "決策邏輯:\n"
                    "1. 判斷股票的特性，並給出依據：\n"
                    "   請評估以下三種屬性的成分佔比 (總和 100%)：\n"
                    "   - 成長股: 營收高成長、產業趨勢向上、新產品爆發\n"
                    "   - 價值股: 基本面穩健、現金流充沛、股息率高\n"
                    "   - 轉機股: 估值低、財務改善、擴廠效益顯現\n"
                    "   - 題材股: 有夢想、技術面強勢、消息面熱絡\n"
                    "2. 你的結論不應只是簡單的資訊堆砌，而必須包含對不同觀點的權衡，並識別出可能的矛盾點（例如：技術面看好但基本面出現警訊）\n"
                    "   範例：\n"
                    "   - 矛盾點: Financial Analyst 警告股價嚴重高估，但 Technical Analyst 指出均線多頭排列且動能強勁\n"
                    "   - 協調裁決: 鑑於該股目前處於「投機股」屬性，我們暫時忽略估值過高問題，優先順勢操作，但設定嚴格停損\n"
                    "3. 部位管理 (依信心分數 0-10):\n"
                    "   - Score > 7: Buy（建倉/加碼）\n"
                    "   - Score 5-6: Hold（觀望/續抱）\n"
                    "   - Score < 5: Sell（減碼/清倉）\n\n"
                    "4. 基於整合後的結論，向使用者提出具體、可操作的建議，並說明背後的邏輯。\n"
                    "完成決策後，請使用 PortfolioDecisions 工具輸出結構化結果。"
                    "市場情況: {market_situation}\n"
                    "本次產生訊號的日期為 {end_date}，會在下個交易日以收盤價做交易\n"
                    "━━━ 新標的分析報告 (ANALYSIS) ━━━\n"
                    "財務分析: {fin_analysis}\n"
                    "技術分析: {tech_analysis}\n"
                    "新聞分析: {news_analysis}\n\n"
                    "━━━ 庫存股驗證報告 (VERIFICATION) ━━━\n"
                    "財務驗證: {fin_verify}\n"
                    "技術驗證: {tech_verify}\n"
                    "新聞驗證: {news_verify}\n\n"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            end_date=end_date,
            market_situation=market_situation,
            fin_analysis=fin_analysis,
            tech_analysis=tech_analysis,
            news_analysis=news_analysis,
            fin_verify=fin_verify,
            tech_verify=tech_verify,
            news_verify=news_verify,
        )
        chain = prompt | llm.bind_tools(tools, tool_choice="any")
        
        return {"messages": [chain.invoke(state["messages"])]}

    def _route(state: PortfolioState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "PortfolioDecisions":
            return "portfolio_format"
        else:
            return "portfolio_tools"

    def _format_node(state: PortfolioState):
        last_msg = state["messages"][-1]
        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "PortfolioDecisions":
                decisions = [
                    PortfolioDecision(**d)
                    for d in (tc["args"].get("portfolio_decisions") or [])
                ]
                return {"portfolio_decisions": decisions}
        return {"portfolio_decisions": []}

    sg = StateGraph(PortfolioState)
    sg.add_node("portfolio_clear",         clear_messages)
    sg.add_node("portfolio_manager", portfolio_manager_node)
    sg.add_node("portfolio_tools",         ToolNode(tools))
    sg.add_node("portfolio_format", _format_node)

    sg.add_edge(START, "portfolio_clear")
    sg.add_edge("portfolio_clear", "portfolio_manager")
    sg.add_conditional_edges("portfolio_manager", _route, ["portfolio_tools", "portfolio_format"])
    sg.add_edge("portfolio_tools", "portfolio_manager")
    sg.add_edge("portfolio_format", END)

    return sg.compile()
