"""
Coordinator subgraph (test version).

create_coordinator(llm) 回傳一個已 compile 的 StateGraph subgraph。
架構與 test.py 的 coordinator 相同：
  SystemMessage（嚴格規則）+ HumanMessage（完整 prompt）
  → LLM（bind tools + CoordinatorOutput）
  → route → tools / format
"""

import operator
from typing import Annotated, List
from typing_extensions import TypedDict

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_utils import get_taiex_data, search_news, get_strategy, get_backtest_report
from tradingagents.agents.utils.agent_output_formats import CoordinatorOutput
from tradingagents.agents.utils.graph_helpers import handle_image_tool_results
from tradingagents.agents.utils.agent_states import CoordinatorState


def create_coordinator(llm):
    """回傳 Coordinator 的 compiled subgraph。"""
    def _tool_name(tool) -> str:
        return getattr(tool, "name", getattr(tool, "__name__", tool.__class__.__name__))
    
    tools = [
        get_taiex_data,
        search_news,
        get_strategy,
        get_backtest_report,
        CoordinatorOutput,
    ]
    def coordinator_node(state: CoordinatorState):
        system_message = (
            "你是一位金融研究協調員，負責擔任使用者與專業分析團隊之間的橋樑。你需要深入理解使用者的分析目標，並依據目標制定一套周詳的分析計畫。你將根據計畫，將任務精準的分配給相應的專家。"
            + " 可用的專家: Financial Analyst(專注於財務報表與公司基本面分析), Technical Analyst(專注於股價圖表與技術指標分析), News Analyst(專注於供應鏈分析、擴產/併購新聞、新產品潛力分析、產業趨勢分析)。"
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "{system_message}\n"
                    "收到使用者輸入後，請依照以下邏輯判斷並分派任務。\n"
                    "情境 A：單點查詢 - 使用者詢問關於特定公司的分析，或是當前市場狀況的分析。此時請協調員根據使用者的需求，制定一套分析計畫，並將任務分配給相應的專家。例如，如果使用者詢問某公司的基本面分析，協調員可能會分配任務給 Financial Analyst 來分析該公司的財務報表和基本面資訊；如果使用者詢問技術分析，則可能會分配任務給 Technical Analyst 來分析該公司的股價圖表和技術指標；如果使用者詢問新聞分析，則可能會分配任務給 News Analyst 來分析與該公司相關的新聞資訊。\n"
                    "情境 B：月度投資組合調整 - 使用者詢問關於某隻量化策略的優化，或是詢問投資組合調整建議。此時請協調員根據使用者的需求，制定一套分析計畫，並將任務分配給相應的專家，任務類型要設為 'ANALYSIS'。例如，如果使用者詢問某隻量化策略的優化，協調員可能會分配任務給 Technical Analyst 來分析投資組合中每隻股票的技術指標和趨勢；也會分配任務給 Financial Analyst 來分析投資組合中各個股票的基本面資訊，以及分配任務給 News Analyst 來分析與投資組合公司的新聞資訊。\n"
                    "- 不得分配大盤或ETF相關任務給專家，這部分應該盡你可能的去分析並提供給專家作為分析背景資訊，但不應該成為專家任務的核心。\n"
                    "- 若有要求某隻量化策略的優化，使用 `get_strategy` 查詢這隻策略的相關資訊,`get_backtest_report` 獲取量化策略的投資組合，任務類型設為 'ANALYSIS'；"
                    "對於所有問題，務必先使用 `get_taiex_data`, `search_news` 了解宏觀市場情況(不應該去搜尋個股新聞)，並將市場情況作為分析背景提供給專家。\n"
                    "一旦完成資料收集，你必須「立刻」呼叫 `CoordinatorOutput` 輸出結構化結果，嚴禁重複呼叫已有結果的工具"
                    "你可以使用下列工具取得額外資訊: {tool_names}.\n",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([_tool_name(tool) for tool in tools]))
        chain = prompt | llm.bind_tools(tools, tool_choice="any")

        return {"messages": [chain.invoke(state["messages"])]}

    def _route(state: CoordinatorState):
        messages = state.get("messages")
        last_message = messages[-1]

        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "CoordinatorOutput":
            return "coordinator_format"
        else:
            return "coordinator_tools"

    def _format_node(state: CoordinatorState):
        last_msg = state["messages"][-1]
        for tc in (last_msg.tool_calls or []):
            if tc["name"] == "CoordinatorOutput":
                args = tc["args"]

                def _is_valid_symbol(task) -> bool:
                    if not task:
                        return False
                    symbol = task.get("symbol") if isinstance(task, dict) else getattr(task, "symbol", None)
                    if not symbol:
                        return False
                    sym = str(symbol).strip()
                    if "_" in sym or " " in sym:
                        return False
                    if len(sym) > 12:
                        return False
                    return True

                def _filter_tasks(tasks):
                    return [t for t in (tasks or []) if _is_valid_symbol(t)]

                financial_tasks = _filter_tasks(args.get("financial_tasks"))
                technical_tasks = _filter_tasks(args.get("technical_tasks"))
                news_tasks      = _filter_tasks(args.get("news_tasks"))

                mode     = args.get("mode", "query")
                end_date = args.get("end_date", "")
                strategy = args.get("strategy", "")

                # --- DEBUG ---
                print(f"\n[Coordinator] CoordinatorOutput produced:")
                print(f"  mode       : {mode}")
                print(f"  end_date   : {end_date}")
                print(f"  strategy   : {strategy}")
                print(f"  financial_tasks ({len(financial_tasks)}): {financial_tasks}")
                print(f"  technical_tasks ({len(technical_tasks)}): {technical_tasks}")
                print(f"  news_tasks  ({len(news_tasks)}): {news_tasks}")

                return {
                    "mode":             mode,
                    "market_situation": args.get("market_situation", ""),
                    "end_date":         end_date,
                    "strategy":         strategy,
                    "financial_tasks":  financial_tasks,
                    "technical_tasks":  technical_tasks,
                    "news_tasks":       news_tasks,
                }
        return {
            "mode": "query", "market_situation": "", "end_date": "",
            "strategy": "", "financial_tasks": [], "technical_tasks": [], "news_tasks": [],
        }

    sg = StateGraph(CoordinatorState)
    sg.add_node("coordinator_llm",           coordinator_node)
    sg.add_node("coordinator_tools",         ToolNode(tools))
    sg.add_node("coordinator_image_handler", handle_image_tool_results)
    sg.add_node("coordinator_format",        _format_node)

    sg.add_edge(START, "coordinator_llm")
    sg.add_conditional_edges("coordinator_llm", _route, ["coordinator_tools", "coordinator_format"])
    sg.add_edge("coordinator_tools", "coordinator_image_handler")
    sg.add_edge("coordinator_image_handler", "coordinator_llm")
    sg.add_edge("coordinator_format", END)

    return sg.compile()
