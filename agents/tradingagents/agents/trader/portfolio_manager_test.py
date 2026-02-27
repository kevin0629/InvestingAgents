"""
Portfolio Manager subgraph (test version).

create_portfolio_manager(llm) 回傳一個已 compile 的 StateGraph subgraph。
Portfolio Manager 同時接收 AnalysisReport（新標的）與 VerificationReport（庫存股驗證），
以及 Critic 的反思教訓，最終輸出投資組合決策。
"""

import operator
from typing import Annotated, List
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_output_formats import (
    FinancialAnalysisReport,
    FinancialVerificationReport,
    TechnicalAnalysisReport,
    TechnicalVerificationReport,
    NewsAnalysisReport,
    NewsVerificationReport,
    PortfolioDecision,
    PortfolioDecisions,
)


class PortfolioSubgraphState(TypedDict):
    user_query: str
    critic_reflections: List[str]
    messages: Annotated[List[AnyMessage], add_messages]
    # Analysis reports（新標的）
    financial_analysis_reports: List[FinancialAnalysisReport]
    technical_analysis_reports: List[TechnicalAnalysisReport]
    news_analysis_reports: List[NewsAnalysisReport]
    # Verification reports（庫存股）
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]
    portfolio_decisions: Annotated[List[PortfolioDecision], operator.add]


def create_portfolio_manager(llm):
    """回傳 Portfolio Manager 的 compiled subgraph。"""

    def portfolio_manager_node(state: PortfolioSubgraphState):
        fin_analysis   = state.get("financial_analysis_reports") or []
        tech_analysis  = state.get("technical_analysis_reports") or []
        news_analysis  = state.get("news_analysis_reports") or []
        fin_verify     = state.get("financial_verification_reports") or []
        tech_verify    = state.get("technical_verification_reports") or []
        news_verify    = state.get("news_verification_reports") or []
        critic_summary = "\n".join(state.get("critic_reflections") or [])

        msgs = [HumanMessage(content=(
            "你是擁有最終裁量權的投資長。你的工作是做出投資決策。\n"
            "你需要綜合考量分析師的報告、市場情況、歷史教訓，"
            "目標是建構一個「高勝率」且「風險可控」的投資組合。\n"
            "當子 Agent 意見分歧時，由你進行最終裁決。\n\n"
            "━━━ 新標的分析報告 (ANALYSIS) ━━━\n"
            f"財務分析: {fin_analysis}\n"
            f"技術分析: {tech_analysis}\n"
            f"新聞分析: {news_analysis}\n\n"
            "━━━ 庫存股驗證報告 (VERIFICATION) ━━━\n"
            f"財務驗證: {fin_verify}\n"
            f"技術驗證: {tech_verify}\n"
            f"新聞驗證: {news_verify}\n\n"
            f"━━━ Critic 反思教訓 ━━━\n{critic_summary}\n\n"
            f"━━━ 使用者需求 ━━━\n{state['user_query']}\n\n"
            "決策邏輯:\n"
            "1. 根據市場情況調整信任權重:\n"
            "   - Bull Market: 重視 News (題材) 與 Financial (成長)。建議 Fin 40% / News 40% / Tech 20%\n"
            "   - Bear/Choppy Market: 重視 Financial (估值保護) 與 Technical (支撐防守)。建議 Fin 50% / Tech 30% / News 20%\n"
            "2. 訊號衝突解決:\n"
            "   - Financial 評為 strong_sell（地雷/假帳風險）→ 無論技術面多好，一律拒絕買進\n"
            "   - Technical 評為 strong_sell（趨勢完全破壞）→ 除非超長線價值投資，否則暫緩買進\n"
            "3. 部位管理 (依信心分數 0-10):\n"
            "   - Score > 8: Aggressive Buy（建倉/加碼 10-15% 權重）\n"
            "   - Score 7: Buy（建倉 5-8% 權重）\n"
            "   - Score 5-6: Hold（觀望/續抱）\n"
            "   - Score < 5: Sell（減碼/清倉）"
        ))]
        return {"messages": [llm.invoke(msgs)]}

    def _format_node(state: PortfolioSubgraphState):
        final_text = state["messages"][-1].content
        result = llm.with_structured_output(PortfolioDecisions).invoke(
            f"根據以下分析，生成投資組合決策。\n"
            f"使用者需求: {state['user_query']}\n"
            f"投資長分析結果: {final_text}"
        )
        return {"portfolio_decisions": result.portfolio_decisions or []}

    sg = StateGraph(PortfolioSubgraphState)
    sg.add_node("portfolio_manager", portfolio_manager_node)
    sg.add_node("format", _format_node)

    sg.add_edge(START, "portfolio_manager")
    sg.add_edge("portfolio_manager", "format")
    sg.add_edge("format", END)

    return sg.compile()
