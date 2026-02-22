from tradingagents.agents.utils.agent_utils import retrieve_reflections
from tradingagents.agents.utils.agent_output_formats import PortfolioDecisions
from langchain_core.messages import HumanMessage



def create_portfolio_manager(llm):
    def portfolio_manager_node(state) -> dict:
        def _extract_payload(result, output_tool_name):
            tool_calls = getattr(result, "tool_calls", None) or []
            for call in tool_calls:
                if call.get("name") == output_tool_name:
                    return call.get("args", {}) or {}
            content = getattr(result, "content", None)
            if isinstance(content, dict):
                return content
            return {}

        def _tool_name(tool):
            return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))
        
        tools = [PortfolioDecisions]
        tool_names = ", ".join([_tool_name(tool) for tool in tools])

        def _get_value(payload, key, default=""):
            if payload is None:
                return default
            if isinstance(payload, dict):
                return payload.get(key, default)
            return getattr(payload, key, default)

        task_payload = state.get("technical_task")
        if task_payload is None:
            technical_tasks = state.get("technical_tasks") or []
            if isinstance(technical_tasks, list) and technical_tasks:
                task_payload = technical_tasks[0]
            elif isinstance(technical_tasks, dict):
                task_payload = technical_tasks.get("task")

        user_query = _get_value(state, "user_query", "")
        mode = _get_value(state, "mode", "")
        market_situation = _get_value(state, "market_situation", "")
        strategy = _get_value(state, "strategy", "")

        financial_analysis_reports = _get_value(state, "financial_analysis_reports", [])
        technical_analysis_reports = _get_value(state, "technical_analysis_reports", [])
        news_analysis_reports = _get_value(state, "news_analysis_reports", [])
        financial_verification_reports = _get_value(state, "financial_verification_reports", [])
        technical_verification_reports = _get_value(state, "technical_verification_reports", [])
        news_verification_reports = _get_value(state, "news_verification_reports", [])


        prompt = f"""你是擁有最終裁量權的投資長。你的工作是做出投資決策。你需要綜合考量分析師的報告、市場情況、歷史教訓，你的目標是建構一個「高勝率」且「風險可控」的投資組合。你必須具備批判性思維，當子 Agent 意見分歧時，由你進行最終裁決。\n
        依據不同模式做出不同的決策邏輯，目前模式為{mode}:\n
        - 單點查詢模式 (query): 主要任務是對特定股票做出買進/賣出/持有的建議。你需要根據{user_query}給出答覆。
        - 月度調整模式 (strategy): 主要任務是對整體投資組合做出調整建議。你需要評估每個持股的表現，並根據分析師的報告、市場情況和投資策略，給出具體的調整建議（例如：加碼、減碼、或維持不變）。

        來自三個子的詳細分析結果與評分: {financial_analysis_reports}、{technical_analysis_reports}、{news_analysis_reports}\n
        來自三個子的驗證報告: {financial_verification_reports}、{technical_verification_reports}、{news_verification_reports}\n
        當前的市場情況是: {market_situation}\n
        你的投資策略是: {strategy}\n
        
決策邏輯:\n
1. 根據市場情況調整對各分析師的信任權重: 例如在 Bull Market: 重視 News (題材) 與 Financial (成長)。權重範例：Fin 40% / News 40% / Tech 20%。;
   Bear/Choppy Market (空頭/震盪): 重視 Financial (估值保護) 與 Technical (支撐防守)。權重範例：Fin 50% / Tech 30% / News 20%。
2. 訊號衝突解決: 若 Financial 評為 "Strong_Sell" (有地雷/假帳風險)，無論技術面多好，一律拒絕買進。若 Technical 評為 "Strong_Sell" (趨勢完全破壞)，除非是超長線價值投資，否則暫緩買進。
3. 部位管理: 根據最終信心分數 (0-10) 決定動作，Score > 8: Aggressive Buy (建倉/加碼 10-15% 權重)，Score 7: Buy (建倉 5-8% 權重)，Score 5~6: Hold (觀望/續抱)。Score < 5: Sell (減碼/清倉)
"""
# 待加入: 你可以從 {tool_names} 中檢索過去的投資決策反思與教訓，以避免重蹈覆轍\n
        try:
            llm_with_tools = llm.bind_tools(tools, tool_choice="any")
        except Exception:
            llm_with_tools = llm.bind_tools(tools)

        messages = list(state.get("portfolio_messages", []))
        if not messages:
            messages = [HumanMessage(content=prompt)]
        result = llm_with_tools.invoke(messages)

        report = _extract_payload(result, PortfolioDecisions.__name__)
        portfolio_decisions = report.get("portfolio_decisions", [])

        output = {"portfolio_messages": [result]}
        if portfolio_decisions:
            output["portfolio_decisions"] = portfolio_decisions
        return output

    return portfolio_manager_node
