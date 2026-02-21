from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import get_taiex_data, search_news, get_strategy, get_backtest_report
from tradingagents.agents.utils.agent_output_formats import CoordinatorOutput


def create_coordinator(llm):
    def coordinator_node(state):
        tools = [
            get_taiex_data,
            search_news,
            get_strategy,
            get_backtest_report,
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
                    " - 若有要求某隻量化策略的優化，使用 `get_strategy` 查詢這隻策略的相關資訊,`get_backtest_report` 獲取量化策略的投資組合，任務類型設為 'ANALYSIS'；除此之外務必使用 `get_holdings` 獲取目前投資組合持股資訊，並將持股資訊提供給專家作為分析依據，而且要將任務類型要設為 'VERIFICATION'。"
                    " 你可以使用下列工具取得額外資訊: {tool_names}.\n",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))

        structured_llm = llm.with_structured_output(CoordinatorOutput)
        chain = prompt | structured_llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        market_situation = ""
        end_date = ""
        
        strategy = ""
        technical_tasks = None
        fundamental_tasks = None
        news_tasks = None

        if len(result.tool_calls) == 0:
            market_situation = result.market_situation
            end_date = result.end_date
            strategy = result.strategy
            technical_tasks = result.technical_tasks
            fundamental_tasks = result.fundamental_tasks
            news_tasks = result.news_tasks

        return {
            "market_situation": market_situation,
            "end_date": end_date,
            "strategy": strategy,
            "technical_tasks": technical_tasks,
            "fundamental_tasks": fundamental_tasks,
            "news_tasks": news_tasks,
        }

    return coordinator_node
