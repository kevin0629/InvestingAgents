from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_taiex_data, search_news, get_strategy, get_backtest_report
from tradingagents.agents.utils.agent_output_formats import CoordinatorOutput


def create_coordinator(llm):
    def coordinator_node(state):
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

        tools = [
            get_taiex_data,
            search_news,
            get_strategy,
            get_backtest_report,
            CoordinatorOutput,
        ]

        system_message = (
            "你是一位金融研究協調員，負責擔任使用者與專業分析團隊之間的橋樑。你需要深入理解使用者的分析目標，並依據目標制定一套周詳的分析計畫。你將根據計畫，將任務精準的分配給相應的專家。"
            + " 可用的專家: Financial Analyst(專注於財務報表與公司基本面分析), Technical Analyst(專注於股價圖表與技術指標分析), News Analyst(專注於供應鏈分析、擴產/併購新聞、新產品潛力分析、產業趨勢分析)。"
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "{system_message}\n"
                    " 收到使用者輸入後，請依照以下邏輯判斷並分派任務。\n"
                    " 情境 A：單點查詢 - 使用者詢問關於特定公司的分析，或是當前市場狀況的分析。此時請協調員根據使用者的需求，制定一套分析計畫，並將任務分配給相應的專家。例如，如果使用者詢問某公司的基本面分析，協調員可能會分配任務給 Financial Analyst 來分析該公司的財務報表和基本面資訊；如果使用者詢問技術分析，則可能會分配任務給 Technical Analyst 來分析該公司的股價圖表和技術指標；如果使用者詢問新聞分析，則可能會分配任務給 News Analyst 來分析與該公司相關的新聞資訊。\n"
                    " 情境 B：月度投資組合調整 - 使用者詢問關於某隻量化策略的優化，或是詢問投資組合調整建議。此時請協調員根據使用者的需求，制定一套分析計畫，並將任務分配給相應的專家，任務類型要設為 'ANALYSIS'。例如，如果使用者詢問某隻量化策略的優化，協調員可能會分配任務給 Technical Analyst 來分析投資組合中每隻股票的技術指標和趨勢；也會分配任務給 Financial Analyst 來分析投資組合中各個股票的基本面資訊，以及分配任務給 News Analyst 來分析與投資組合公司的新聞資訊。\n"
                    " - 若有要求某隻量化策略的優化，使用 `get_strategy` 查詢這隻策略的相關資訊,`get_backtest_report` 獲取量化策略的投資組合，任務類型設為 'ANALYSIS'；"
                    " 你可以使用下列工具取得額外資訊: {tool_names}.\n",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        # 待加入 prompt 除此之外務必使用 `get_holdings` 獲取目前投資組合持股資訊，並將持股資訊提供給專家作為分析依據，而且要將任務類型要設為 'VERIFICATION'。

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([_tool_name(tool) for tool in tools]))

        try:
            llm_with_tools = llm.bind_tools(tools, tool_choice="any")
        except Exception:
            llm_with_tools = llm.bind_tools(tools)

        chain = prompt | llm_with_tools

        result = chain.invoke({"messages": state.get("messages", [])})

        report = _extract_payload(result, CoordinatorOutput.__name__)

        def _is_valid_symbol(task) -> bool:
            """Reject pseudo-symbol slugs — only accept real exchange tickers."""
            if not task:
                return False
            symbol = task.get("symbol") if isinstance(task, dict) else getattr(task, "symbol", None)
            if not symbol:
                return False
            sym = str(symbol).strip()
            # Reject if it contains underscores/spaces or is clearly descriptive (>12 chars with no digits)
            if "_" in sym or " " in sym:
                return False
            if len(sym) > 12:
                return False
            return True

        def _filter_tasks(tasks):
            if not tasks:
                return []
            return [t for t in tasks if _is_valid_symbol(t)]

        if not report:
            return {
                "messages": [result],
            }

        user_query = report.get("user_query", state.get("user_query", ""))
        mode = report.get("mode", state.get("mode", ""))
        market_situation = report.get("market_situation", state.get("market_situation", ""))
        end_date = report.get("end_date", state.get("end_date", ""))
        strategy = report.get("strategy", state.get("strategy", ""))
        technical_tasks = _filter_tasks(report.get("technical_tasks", state.get("technical_tasks", [])))
        financial_tasks = _filter_tasks(report.get("financial_tasks", state.get("financial_tasks", [])))
        news_tasks = _filter_tasks(report.get("news_tasks", state.get("news_tasks", [])))

        # --- DEBUG ---
        print(f"\n[Coordinator] CoordinatorOutput produced:")
        print(f"  mode       : {mode}")
        print(f"  end_date   : {end_date}")
        print(f"  strategy   : {strategy}")
        print(f"  financial_tasks ({len(financial_tasks)}): {financial_tasks}")
        print(f"  technical_tasks ({len(technical_tasks)}): {technical_tasks}")
        print(f"  news_tasks  ({len(news_tasks)}): {news_tasks}")

        return {
            "messages": [result],
            "user_query": user_query,
            "mode": mode,
            "market_situation": market_situation,
            "end_date": end_date,
            "strategy": strategy,
            "technical_tasks": technical_tasks,
            "financial_tasks": financial_tasks,
            "news_tasks": news_tasks,
        }

    return coordinator_node
