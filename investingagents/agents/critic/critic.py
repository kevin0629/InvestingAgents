from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from agents.agent_states import CriticState
from agents.utils import clear_messages
from tools import (
    get_tools,
    retrieve_reflections,
    store_reflections,
)


def create_critic(llm):
    """
    只在有 VerificationReport 時才會被呼叫（由 route_after_analysts 控制）。
    """

    tools = [
        retrieve_reflections,
        store_reflections,
    ]

    tool_names = get_tools(tools)

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
            buy_reason = report.get("buy_reason")
            review_comment = report.get("review_comment")
            report_text = report.get("report")

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

            return "\n".join(lines) if lines else str(report)

        return str(report)

    def _reports_to_markdown(title, reports):
        if reports is None:
            return f"### {title}\n- 無資料"

        if isinstance(reports, dict):
            rows = [reports]
        else:
            rows = reports or []

        if not rows:
            return f"### {title}\n- 無資料"

        chunks = [f"### {title}"]
        for index, row in enumerate(rows, start=1):
            chunks.append(f"#### {title} #{index}")
            chunks.append(_report_to_markdown(row))
        return "\n\n".join(chunks)

    def _build_previous_holdings_summary(previous_holdings_context):
        rows = previous_holdings_context or []
        if not rows:
            return "- 無上一期持股資料"

        lines = []
        for row in rows:
            symbol = str((row or {}).get("symbol") or "").strip()
            if not symbol:
                continue
            position = (row or {}).get("position")
            stock_return = str((row or {}).get("stock_return") or "").strip()
            buy_reason = str((row or {}).get("buy_reason") or "").strip()
            lines.append(
                f"- {symbol}: position={position if position is not None else 'N/A'}, "
                f"return={round(float(stock_return), 2) if stock_return else 'N/A'}%, buy_reason={buy_reason or 'N/A'}"
            )

        return "\n".join(lines) if lines else "- 無上一期持股資料"

    def critic_node(state: CriticState):
        end_date = state.get("end_date")
        strategy = state.get("strategy")
        pre_market_performance = state.get("pre_market_performance")
        pre_strategy_performance = state.get("pre_strategy_performance")
        pre_performance = state.get("pre_performance")
        previous_holdings_summary = _build_previous_holdings_summary(state.get("previous_holdings_context"))

        reports_summary = "\n\n".join(
            [
                _reports_to_markdown("財務驗證報告", state.get("financial_verification_reports")),
                _reports_to_markdown("技術驗證報告", state.get("technical_verification_reports")),
                _reports_to_markdown("新聞驗證報告", state.get("news_verification_reports")),
                _reports_to_markdown("宏觀分析報告", state.get("macro_analysis_report")),
            ]
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位專業且嚴謹的投資決策事後檢討稽核員，負責對過去持倉進行歸因分析，找出投資決策成功或失敗的根本原因，並將結果轉化為可優化未來決策的具體規則。\n"
                    "過去持倉的投資決策是基於 {strategy} 策略篩出的股票，再由 Portfolio Manager 進一步選出較好的標的進行投資。\n"
                    "目標：透過對過去持倉的嚴謹歸因與檢討，將檢討結果轉化為可執行的價值導向決策規則，以期中長期穩定超越大盤及 {strategy} 原始績效。\n"
                    "你的分析將直接影響投資策略優化，因此必須確保邏輯一致、歸因準確，並避免後見之明偏誤。\n"
                    "交易規則：交易頻率為每月一次，每次都會做滿倉位。不執行分批建倉、減倉、停損或停利等交易管理設定。\n"
                    "你的核心目標是：\n"
                    "1. 驗證當初投資假設是否成立\n"
                    "2. 判斷股價結果是否符合預期\n"
                    "3. 分析成功或失敗的真正原因（歸因）\n"
                    "4. 提煉可重複使用的投資原則\n\n"
                    "你的分析必須遵循以下原則：\n"
                    "- 採用「事實 → 歸因 → 偏誤 → 原則」分析流程\n"
                    "- 僅根據驗證報告內容進行分析，不得自行假設未提供的資訊\n"
                    "上一期大盤表現: {pre_market_performance}\n"
                    "上一期 {strategy} 策略表現: {pre_strategy_performance}\n"
                    "上一期投資決策表現: {pre_performance}\n"
                    "上一期持股（供報酬歸因參考）:\n{previous_holdings_summary}\n"
                    "Financial 、Technical、News Analyst、Macro Analyst 提供的驗證分析報告:\n"
                    "{reports_summary}\n"
                    "你可以使用的工具: {tool_names}\n, 在使用`store_reflections`之前務必使用`retrieve_reflections`回顧之前的檢討內容，避免重複內容存入。"
                    "`store_reflections`只能依據 Financial 、Technical、News Analyst、Macro Analyst 提供的驗證分析報告才產生反思，不可以將你的胡思亂想內容胡亂存入，務必確保反思內容是有根據的、具體的、且能夠提煉出可執行的投資原則的。\n"
                    "所有工具呼叫的 end_date 參數皆必須設為 {end_date}，為本次資料分析截止日期，嚴禁使用截止日期以後的資料。\n\n"
                    "分析方法:\n"
                    "Step1: 事實核對\n"
                    "- 情境 A：預測發生了，股價也漲了 → 決策正確（記錄成功模式）\n"
                    "- 情境 B：預測發生了，但股價跌了 → 市場定價錯誤 或 忽略了其他風險（需深度檢討）\n"
                    "- 情境 C：預測沒發生（例如營收不如預期） → 分析失準（需檢討分析邏輯）\n\n"
                    "Step 2: 歸因分析\n"
                    "- 基本面是否如預期\n"
                    "- 技術面是否如預期\n"
                    "- 新聞面是否如預期\n"
                    "Step3: 偏誤識別\n"
                    "- 確認偏誤\n"
                    "- 過度樂觀\n"
                    "- 忽略風險\n"
                    "- 訊號衝突忽視\n"
                    "Step4: 提煉教訓\n"
                    "- 將分析結果轉化為通用的可執行規則，例如：若基本面改善但技術面為空頭排列 → 不進場\n"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(
            reports_summary=reports_summary,
            pre_market_performance=pre_market_performance,
            pre_strategy_performance=pre_strategy_performance,
            pre_performance=pre_performance,
            previous_holdings_summary=previous_holdings_summary,
            strategy=strategy,
            end_date=end_date,
        )
        prompt = prompt.partial(tool_names=tool_names)
        chain = prompt | llm.bind_tools(tools)
        
        return {"messages": [chain.invoke(state["messages"])]}

    def _route(state: CriticState):
        messages = state.get("messages") or []
        if not messages:
            return "critic_format"

        last_message = messages[-1]
        if getattr(last_message, "tool_calls", None):
            return "critic_tools"
        return "critic_format"

    def _format_node(state: CriticState):
        messages = state.get("messages") or []
        if not messages:
            return {"critic_reflections": []}

        final_text = messages[-1].content
        return {"critic_reflections": [final_text]}

    sg = StateGraph(CriticState)
    sg.add_node("critic_clear", clear_messages)
    sg.add_node("critic_llm", critic_node)
    sg.add_node("critic_tools", ToolNode(tools))
    sg.add_node("critic_format", _format_node)

    sg.add_edge(START, "critic_clear")
    sg.add_edge("critic_clear", "critic_llm")
    sg.add_conditional_edges("critic_llm", _route, ["critic_tools", "critic_format"])
    sg.add_edge("critic_tools", "critic_llm")
    sg.add_edge("critic_format", END)

    return sg.compile()
