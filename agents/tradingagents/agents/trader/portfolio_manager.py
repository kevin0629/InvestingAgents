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
from tradingagents.agents.utils.agent_utils import (
    get_tools,
    create_stock_holding,
    retrieve_reflections
)


def _filter_selected_verifications(reports):
    selected_reports = []
    for report in reports or []:
        report_selected = False
        if isinstance(report, dict):
            report_selected = bool(report.get("selected"))
        else:
            report_selected = bool(getattr(report, "selected", False))
        if report_selected:
            selected_reports.append(report)
    return selected_reports


def create_portfolio_manager(llm):
    """回傳 Portfolio Manager 的 compiled subgraph。"""
    tools = [
        create_stock_holding,
        retrieve_reflections,
        PortfolioDecisions
    ]
    tool_names = get_tools(tools)

    def portfolio_manager_node(state: PortfolioState):
        end_date = state.get("end_date")
        strategy = state.get("strategy")

        fin_analysis   = state.get("financial_analysis_reports") or []
        tech_analysis  = state.get("technical_analysis_reports") or []
        news_analysis  = state.get("news_analysis_reports") or []
        macro_analysis = state.get("macro_analysis_report")
        fin_verify_selected = _filter_selected_verifications(state.get("financial_verification_reports"))
        tech_verify_selected = _filter_selected_verifications(state.get("technical_verification_reports"))
        news_verify_selected = _filter_selected_verifications(state.get("news_verification_reports"))

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是擁有最終裁量權的投資長，負責整合各分析師的報告，做出最終投資決策，並管理投資組合風險。\n"
                    "你的目標是從 {strategy} 策略中，建構一個高勝率、高報酬且風險可控的投資組合。\n"
                    "你的核心目標是：\n"
                    "1. 整合多來源分析\n"
                    "2. 解決分析之間的矛盾\n"
                    "3. 評估整體風險與報酬\n"
                    "4. 做出可執行的投資決策(Buy Only)\n\n"
                    "你的決策必須遵循以下原則：\n"
                    "- 採用風險優先原則，若存在重大風險（macro 轉空 / 財務惡化），優先降低評級\n"
                    "- 採用多訊號整合方法，不得僅依單一分析做決策\n"
                    "- 當訊號衝突時，必須明確說明並做出裁決\n\n"
                    "市場情況: {macro_analysis}\n"
                    "本次產生訊號的日期為 {end_date}，會在下個交易日以收盤價做交易\n"
                    "股票池分析報告：\n"
                    "財務分析: {fin_analysis}\n"
                    "技術分析: {tech_analysis}\n"
                    "新聞分析: {news_analysis}\n"
                    "財務驗證分析: {fin_verify_selected}\n"
                    "技術驗證分析: {tech_verify_selected}\n"
                    "新聞驗證分析: {news_verify_selected}\n\n"
                    "你可以使用的工具: {tool_names}\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，嚴禁使用截止日期以後的資料。\n\n"
                    "決策邏輯:\n"
                    "1. 判斷股票的特性，並給出依據：\n"
                    "   請評估以下四種屬性的成分佔比 (總和 100%)：\n"
                    "   - 成長股: 營收高成長、產業趨勢向上、新產品爆發\n"
                    "   - 價值股: 基本面穩健、現金流充沛、股息率高\n"
                    "   - 轉機股: 估值低、財務改善、擴廠效益顯現\n"
                    "   - 題材股: 有夢想、技術面強勢、消息面熱絡\n"
                    "2. 你的結論不應只是簡單的資訊堆砌，而必須包含對不同觀點的權衡，並識別出可能的矛盾點（例如：技術面看好但基本面出現警訊）\n"
                    "   範例：\n"
                    "   - 矛盾點: Financial Analyst 警告股價嚴重高估，但 Technical Analyst 指出均線多頭排列且動能強勁\n"
                    "   - 協調裁決: 鑑於該股目前處於「投機股」屬性，我們暫時忽略估值過高問題，優先順勢操作，但設定嚴格停損\n"
                    "3. 部位管理 (依信心分數 0-10):\n"
                    "   - Score > 7: Buy\n"
                    "   - Score 5-6: Watchlist\n"
                    "   - Score < 5: Ignore\n\n"
                    "4. 執行兩階段下單流程以利消融實驗（兩次下單皆需執行）：\n"
                    "   - 第一次（初始下單）：依整合後的結論呼叫 `create_stock_holding`，此呼叫必須包含參數 `reflection`: false。\n"
                    "   - 第二次（反思後調整）：接著呼叫 `retrieve_reflections`，取得相關反思要點，將反思融入決策後再次呼叫 `create_stock_holding`，此呼叫必須包含 `reflection`: true。\n"
                    "5. 完成上述兩階段流程後，使用 PortfolioDecisions 工具輸出結構化結果。"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            strategy=strategy,
            end_date=end_date,
            macro_analysis=macro_analysis,
            fin_analysis=fin_analysis,
            tech_analysis=tech_analysis,
            news_analysis=news_analysis,
            fin_verify_selected=fin_verify_selected,
            tech_verify_selected=tech_verify_selected,
            news_verify_selected=news_verify_selected,
        )
        prompt = prompt.partial(tool_names=tool_names)

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
