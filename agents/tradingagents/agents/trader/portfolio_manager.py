"""
Portfolio Manager subgraph (test version).

create_portfolio_manager(llm) 回傳一個已 compile 的 StateGraph subgraph。
Portfolio Manager 同時接收 AnalysisReport（新標的）與 VerificationReport（庫存股驗證），
以及 Critic 的反思教訓，最終輸出投資組合決策。
"""

import json

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    PortfolioDecision,
    PortfolioDecisions,
)
from tradingagents.agents.utils.agent_states import PortfolioState
from tradingagents.agents.utils.agent_utils import (
    get_tools,
    clear_messages,
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


def _report_to_markdown(report):
    if report is None:
        return ""

    if hasattr(report, "model_dump"):
        report = report.model_dump()
    elif hasattr(report, "dict"):
        report = report.dict()

    if isinstance(report, dict):
        symbol = report.get("symbol")
        signal = report.get("signal")
        confidence = report.get("confidence_score")
        selected = report.get("selected")
        report_text = report.get("report")
        buy_reason = report.get("buy_reason")
        review_comment = report.get("review_comment")

        lines = []
        if symbol:
            lines.append(f"- 標的: {symbol}")
        if signal:
            lines.append(f"- 訊號: {signal}")
        if confidence is not None:
            lines.append(f"- 信心分數: {confidence}")
        if selected is not None:
            lines.append(f"- 是否為前後期共同入選: {selected}")
        if buy_reason:
            lines.append(f"- 原始買進理由: {buy_reason}")
        if review_comment:
            lines.append(f"- 檢討意見: {review_comment}")
        if report_text:
            lines.append("- 報告內容:")
            lines.append(f"  {report_text}")

        if lines:
            return "\n".join(lines)
        return json.dumps(report, ensure_ascii=False, indent=2)

    return str(report)


def _reports_to_markdown(title, reports):
    if not reports:
        return f"### {title}\n- 無資料"

    chunks = [f"### {title}"]
    for index, report in enumerate(reports, start=1):
        chunks.append(f"#### {title} #{index}")
        chunks.append(_report_to_markdown(report))
    return "\n\n".join(chunks)


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

        macro_markdown = _report_to_markdown(macro_analysis) or "- 無資料"
        reports_markdown = "\n\n".join(
            [
                _reports_to_markdown("財務分析", fin_analysis),
                _reports_to_markdown("技術分析", tech_analysis),
                _reports_to_markdown("新聞分析", news_analysis),
                _reports_to_markdown("財務驗證分析(僅入選標的)", fin_verify_selected),
                _reports_to_markdown("技術驗證分析(僅入選標的)", tech_verify_selected),
                _reports_to_markdown("新聞驗證分析(僅入選標的)", news_verify_selected),
            ]
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是擁有最終裁量權的投資長，負責在既定策略下做風險控管導向的選股決策。\n"
                    "策略背景：候選股票池已由 {strategy} 策略先行篩出；你的任務是整合各分析師的報告並從該股票池中挑選高品質標的。\n"
                    "目標：在可控風險下，追求績效同時贏過大盤與 {strategy} 策略原始績效。\n"
                    "本次產生訊號的日期為 {end_date}，會在下個交易日以收盤價做交易。\n\n"
                    "風險控管與決策原則：\n"
                    "1. 不做分批建倉、減倉、停損、停利等交易管理設定；本輪只做 Buy / Ignore。\n"
                    "2. 對沒有信心或證據不足的標的，不得買進。\n"
                    "3. 採用風險優先原則：若宏觀轉弱、財務惡化、或訊號衝突無法合理化，應降評或忽略。\n"
                    "4. 採用多訊號整合：財務、技術、新聞必須交叉驗證，且需把宏觀情境融入三者判讀。\n"
                    "5. 當訊號衝突時，必須明確寫出矛盾點與裁決依據。\n\n"
                    "以下提供整理好的報告，請直接閱讀其內容做判斷。\n"
                    "## 宏觀分析\n{macro_markdown}\n\n"
                    "## 股票池報告彙整\n{reports_markdown}\n\n"
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
                    "3. 買進門檻 (依信心分數 0-10):\n"
                    "   - Score > 7: Buy\n"
                    "   - Score <= 7: Ignore\n"
                    "4. 執行兩階段下單流程，每個階段皆只能做一次來模擬真實環境，請務必考量所有股票後再做決策，若沒有要下單的標的此階段可以跳過：\n"
                    "   - 第一次：依整合後的結論呼叫 `create_stock_holding`，此呼叫必須包含參數 `reflection`: false。\n"
                    "   - 第二次：接著呼叫 `retrieve_reflections`，要查詢較通用的邏輯，例如財務/技術/新聞/宏觀/產業的反思，不要查個股；將反思融入決策後再次呼叫 `create_stock_holding`，此呼叫必須包含 `reflection`: true。\n"
                    "5. 完成上述兩階段流程後，使用 PortfolioDecisions 工具輸出結構化結果。"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            strategy=strategy,
            end_date=end_date,
            macro_markdown=macro_markdown,
            reports_markdown=reports_markdown,
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
