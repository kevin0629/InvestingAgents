import operator
from typing import Annotated, List, Literal
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage, RemoveMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langgraph.constants import Send
from langgraph.prebuilt import ToolNode
from tradingagents.agents.utils.agent_utils import (
    get_stock_data,
    get_taiex_data,
    get_company_info,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_monthly_revenue,
    get_factors,
    get_dupont_analysis,
    get_river_chart,
    search_news,
    get_strategy,
    get_backtest_report,
    # store_reflection,
    # retrieve_reflections,
)
from tradingagents.agents.utils.agent_output_formats import *
from tradingagents.agents.utils.agent_states import *



load_dotenv()  # Load environment variables from .env file
llm = ChatOpenAI(model="gpt-5-mini", temperature=0)


def _handle_image_tool_results(state):
    """
    OpenAI does not allow image_url in tool-role messages.
    Strip image blocks from each ToolMessage (update in-place by reusing its id),
    then append a HumanMessage carrying the images so the LLM can still see them.
    Updating by same id keeps the ToolMessage in its original position so the
    sequence AIMessage(tool_calls) → ToolMessage(s) stays valid.
    """
    messages = state["messages"]
    updates = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content
        # ToolNode may serialise list content to a JSON string; handle both
        if isinstance(content, str):
            try:
                import json
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    content = parsed
            except Exception:
                pass

        if not isinstance(content, list):
            continue

        image_blocks = [b for b in content if isinstance(b, dict) and b.get("type") == "image_url"]
        if not image_blocks:
            continue

        text_blocks = [b for b in content if not (isinstance(b, dict) and b.get("type") == "image_url")]
        plain_text = " ".join(
            b["text"] if isinstance(b, dict) and "text" in b else str(b)
            for b in text_blocks
        ) or "圖表已提供。"

        # Update ToolMessage in-place (same id → add_messages replaces, not appends)
        updates.append(ToolMessage(
            id=msg.id,
            content=plain_text,
            tool_call_id=msg.tool_call_id,
            name=msg.name,
        ))
        # Append image as a new user turn AFTER the (now-clean) ToolMessage
        updates.append(HumanMessage(
            content=image_blocks + [{"type": "text", "text": f"{msg.name} 工具返回的圖表如上，請分析。"}]
        ))

    return {"messages": updates} if updates else {}


def clear_messages(state) -> dict:
    """清除所有 messages，防止 agent 之間的 context 洩漏。
    在兩個 node 之間插入此 node 可確保下一個 agent 拿到乾淨的 messages 起點。
    """
    msgs = state.get("messages") or []
    if not msgs:
        return {}
    return {"messages": [RemoveMessage(id=m.id) for m in msgs]}


# Analyst 的 Sub-State (給 Send API 使用)
class AnalystState(TypedDict):
    task: Task

# ==========================================
# 2. Tools (from agent_utils, distributed per agent role)
# ==========================================
# coordinator: market overview tools
_coordinator_tools = [get_strategy, get_backtest_report, get_taiex_data, search_news]

# financial: fundamental data tools
_financial_tools = [
    get_company_info,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_monthly_revenue,
    get_factors,
    get_dupont_analysis,
    get_river_chart,
]

# technical: price / indicator data
_technical_tools = [get_stock_data]

# news: news & company background
_news_tools = [get_company_info, search_news]

# ==========================================
# 3. Subgraph Nodes
# ==========================================

# --- 1. Coordinator Subgraph ---
class CoordinatorSubgraphState(TypedDict):
    user_query: str
    mode: Annotated[str, "Operation mode: query or strategy"]
    market_situation: Annotated[str, "Current market situation"]
    end_date: Annotated[str, "End time for the data usage and trading decision"]
    messages: Annotated[List[AnyMessage], add_messages]
    financial_tasks: Annotated[List[Task], operator.add]
    technical_tasks: Annotated[List[Task], operator.add]
    news_tasks: Annotated[List[Task], operator.add]

_coordinator_llm = llm.bind_tools(_coordinator_tools + [CoordinatorOutput])

_COORDINATOR_SYSTEM = SystemMessage(content=(
    "【嚴格規則】你是一位自動化金融研究協調員，不得向使用者提問、請求確認或建議下一步。"
    "完成所有必要的資料收集後，你必須立刻呼叫 `CoordinatorOutput` 工具輸出結構化結果，不得輸出任何純文字回覆。"
    "若資訊已足夠制定分析計畫，直接呼叫 `CoordinatorOutput`，不得再詢問使用者意見。"
))

def _coordinator_llm_node(state: CoordinatorSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        msgs = [HumanMessage(content=(
            "你是一位金融研究協調員，負責擔任使用者與專業分析團隊之間的橋樑。你需要深入理解使用者的分析目標，並依據目標制定一套周詳的分析計畫。你將根據計畫，將任務精準的分配給相應的專家。\n"
            "可用的專家: Financial Analyst(專注於財務報表與公司基本面分析), Technical Analyst(專注於股價圖表與技術指標分析), News Analyst(專注於供應鏈分析、擴產/併購新聞、新產品潛力分析、產業趨勢分析)。\n"
            "收到使用者輸入後，請依照以下邏輯判斷並分派任務。\n"
            "情境 A：單點查詢 - 使用者詢問關於特定公司的分析，或是當前市場狀況的分析。此時請協調員根據使用者的需求，制定一套分析計畫，並將任務分配給相應的專家。例如，如果使用者詢問某公司的基本面分析，協調員可能會分配任務給 Financial Analyst 來分析該公司的財務報表和基本面資訊；如果使用者詢問技術分析，則可能會分配任務給 Technical Analyst 來分析該公司的股價圖表和技術指標；如果使用者詢問新聞分析，則可能會分配任務給 News Analyst 來分析與該公司相關的新聞資訊。\n"
            "情境 B：月度投資組合調整 - 使用者詢問關於某隻量化策略的優化，或是詢問投資組合調整建議。使用`get_backtest_report` 獲取量化策略的投資組合，使用 `get_strategy` 查詢策略說明。此時請協調員根據使用者的需求，制定一套分析計畫，並將任務分配給相應的專家，任務類型要設為 'ANALYSIS'。例如，如果使用者詢問某隻量化策略的優化，協調員可能會分配任務給 Technical Analyst 來分析投資組合中每隻股票的技術指標和趨勢；也會分配任務給 Financial Analyst 來分析投資組合中各個股票的基本面資訊，以及分配任務給 News Analyst 來分析與投資組合公司的新聞資訊。\n"
            "請分派合理的 symbol 給分析師，而不是給 0000 或 NULL 或 None，這需無法辨識的股票代號。\n"
            "宏觀的分析由你來執行可以使用 `get_taiex_data`, `search_news` 了解市場情況，並將市場情況作為分析背景提供給專家。\n"
            "一家公司只會被分派一次任務給相同的分析師，不得重複分派相同公司的任務給同一位分析師。\n"
            f"使用者需求: {state['user_query']}。\n"
        ))]
    return {"messages": [_coordinator_llm.invoke([_COORDINATOR_SYSTEM] + msgs)]}

def _coordinator_route(state: CoordinatorSubgraphState):
    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return "coordinator_format"
    if any(tc["name"] == "CoordinatorOutput" for tc in tool_calls):
        return "coordinator_format"
    return "coordinator_tools"


def _coordinator_format_node(state: CoordinatorSubgraphState):
    last_msg = state["messages"][-1]
    for tc in (last_msg.tool_calls or []):
        if tc["name"] == "CoordinatorOutput":
            result = CoordinatorOutput(**tc["args"])
            return {
                "mode":             result.mode or "query",
                "market_situation": result.market_situation or "",
                "end_date":         result.end_date or "",
                "strategy":         result.strategy or "",
                "financial_tasks":  result.financial_tasks or [],
                "technical_tasks":  result.technical_tasks or [],
                "news_tasks":       result.news_tasks or [],
            }
    return {"mode": "query", "market_situation": "", "end_date": "", "strategy": "", "financial_tasks": [], "technical_tasks": [], "news_tasks": []}

_coordinator_sg = StateGraph(CoordinatorSubgraphState)
_coordinator_sg.add_node("coordinator_llm", _coordinator_llm_node)
_coordinator_sg.add_node("coordinator_tools", ToolNode(_coordinator_tools))
_coordinator_sg.add_node("coordinator_image_handler", _handle_image_tool_results)
_coordinator_sg.add_node("coordinator_format", _coordinator_format_node)
_coordinator_sg.add_edge(START, "coordinator_llm")
_coordinator_sg.add_conditional_edges("coordinator_llm", _coordinator_route, ["coordinator_tools", "coordinator_format"])
_coordinator_sg.add_edge("coordinator_tools", "coordinator_image_handler")
_coordinator_sg.add_edge("coordinator_image_handler", "coordinator_llm")
_coordinator_sg.add_edge("coordinator_format", END)
coordinator_agent = _coordinator_sg.compile()

# --- 2. 核心路由邏輯 (Map 階段) ---
def route_tasks(state: AgentState):
    print("🔀 [Router] 透過 Send API 平行派發任務給各 Agent...")
    end_date = state.get("end_date", "")
    sends = []
    for task in state.get("financial_tasks", []):
        sends.append(Send("financial_agent", {"task": task, "end_date": end_date}))
    for task in state.get("technical_tasks", []):
        sends.append(Send("technical_agent", {"task": task, "end_date": end_date}))
    for task in state.get("news_tasks", []):
        sends.append(Send("news_agent", {"task": task, "end_date": end_date}))
    return sends

# --- 3. Financial Agent Subgraph ---
class FinancialSubgraphState(TypedDict):
    task: Task
    end_date: str  # 從父 AgentState 透過 key name matching 自動注入
    messages: Annotated[List[AnyMessage], add_messages]
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add]

_financial_llm = llm.bind_tools(_financial_tools + [FinancialOutput])

def _financial_llm_node(state: FinancialSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        task = state["task"]
        end_date = state["end_date"]
        msgs = [HumanMessage(content=(
            f"你是一位財務分析師，主要任務是{task.task}，次要任務要評估{task.symbol}股價是被低估還是被高估，並分析未來公司股價上升的可能性。"
            f"本次分析的資料截止日期為 {end_date}。所有工具呼叫的 end_date 參數皆必須設為 {end_date}（或更早），絕對不得查詢或引用超過此日期的任何財報、月營收或財務數據。\n"
            f"Step1: task_type 為 {task.task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證{task.buy_reason}有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有。\n"
            "判斷標準範例:\n"
            "- SUCCESS: 數據完全支持當初的論點（例如：預測毛利升，真的升了）\n"
            "- FAILURE: 數據與預測相反（例如：預測營收增，結果持平或衰退）\n"
            "- NEUTRAL: 無法判斷或雜訊過多\n"
            f"Step2: 三大報表分析、財務指標分析、杜邦分析、河流圖分析等工具，從財務面分析{task.symbol}的表現，並評估未來股價上升的可能性。請具體分析財務數據，並給出結論。\n"
            "1. 三大報表分析:\n"
            "- 損益表: 分析近期的營收、毛利、營業利益及淨利，判斷公司的成長趨勢\n"
            "- 資產負債表: 分析公司的資產結構、負債結構及股東權益，評估公司的財務穩健程度\n"
            "- 現金流量表: 分析公司的營運現金流、投資現金流及融資現金流，評估公司的現金流狀況\n"
            "2. 財務指標分析:\n"
            "- 獲利能力指標: 如毛利率、營業利益率、淨利率等，評估公司的獲利能力\n"
            "- 償債能力指標: 如流動比率、負債比率等，評估公司的償債能力\n"
            "- 經營效率指標: 如存貨週轉天數、應收帳款週轉天數等，評估公司的經營效率\n"
            "3. 杜邦分析:\n"
            "- 分析公司的ROE，並拆解成淨利率、資產週轉率和財務槓桿，評估公司的盈利能力和經營效率\n"
            "4. 河流圖分析:\n"
            "- 分析公司目前的本益比位於歷史區間的相對高點、低點或平均水平？ 分析本益比的變動，是否與公司 EPS 增長的趨勢相匹配\n"
            "列出具體的財務風險，例如：應收帳款異常增加\n"
            "你的所有結論都必須基於嚴謹的財務數據與量化證據，並保持客觀中立的判斷，給出投資建議:\n"
            "- strong_buy: 積極關注。公司基本面強勁且股價被錯殺，具有極高的安全邊際，適合長線投資人分批佈局。\n"
            "- buy: 持有/續抱。公司在合理的價格，建議持有並關注營收成長動能是否延續。\n"
            "- neutral: 謹慎持有。市場已給予高期待。股價對財報容錯率低，建議關注成長率是否放緩，不宜大舉追高。\n"
            "- sell: 迴避/減碼。股價嚴重脫離基本面，風險極高，建議遠離或獲利了結。\n"
            "- strong_sell: 觀望。嚴重脫離基本面，且出現財務警訊 (如現金流轉負)。"
        ))]
    return {"messages": [_financial_llm.invoke(msgs)]}

def _financial_route(state: FinancialSubgraphState):
    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return "financial_format"
    if any(tc["name"] == "FinancialOutput" for tc in tool_calls):
        return "financial_format"
    return "financial_tools"

def _financial_format_node(state: FinancialSubgraphState):
    last_msg = state["messages"][-1]
    for tc in (last_msg.tool_calls or []):
        if tc["name"] == "FinancialOutput":
            args = tc["args"]
            analysis     = [FinancialAnalysisReport(**r)     for r in (args.get("financial_analysis_reports")     or [])]
            verification = [FinancialVerificationReport(**r) for r in (args.get("financial_verification_reports") or [])]
            return {
                "financial_analysis_reports":     analysis,
                "financial_verification_reports": verification,
            }
    return {"financial_analysis_reports": [], "financial_verification_reports": []}

_financial_sg = StateGraph(FinancialSubgraphState)
_financial_sg.add_node("financial_clear", clear_messages)  # 隔離父 graph 的 messages
_financial_sg.add_node("financial_llm", _financial_llm_node)
_financial_sg.add_node("financial_tools", ToolNode(_financial_tools))
_financial_sg.add_node("financial_image_handler", _handle_image_tool_results)
_financial_sg.add_node("financial_format", _financial_format_node)
_financial_sg.add_edge(START, "financial_clear")
_financial_sg.add_edge("financial_clear", "financial_llm")
_financial_sg.add_conditional_edges("financial_llm", _financial_route, ["financial_tools", "financial_format"])
_financial_sg.add_edge("financial_tools", "financial_image_handler")
_financial_sg.add_edge("financial_image_handler", "financial_llm")
_financial_sg.add_edge("financial_format", END)
financial_agent = _financial_sg.compile()

# --- 4. Technical Agent Subgraph ---
class TechnicalSubgraphState(TypedDict):
    task: Task
    end_date: str  # 從父 AgentState 透過 key name matching 自動注入
    messages: Annotated[List[AnyMessage], add_messages]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add]

_technical_llm = llm.bind_tools(_technical_tools + [TechnicalOutput])

def _technical_llm_node(state: TechnicalSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        task = state["task"]
        end_date = state["end_date"]
        msgs = [HumanMessage(content=(
            f"你是一位技術分析師，主要任務是{task.task}，次要任務是分析{task.symbol}的價格、成交量與技術指標，並進一步判讀未來的走勢。\n"
            f"本次分析的資料截止日期為 {end_date}。所有工具呼叫的 end_date 參數皆必須設為 {end_date}，絕對不得使用超過此日期的任何價格或技術指標資料。\n"
            f"任務指引: task_type 為 {task.task_type}。若 `task_type` 是 VERIFICATION，代表這是庫存股，你必須先驗證 上其購買理由({task.buy_reason}) 有沒有符合預期，並偵測盲點，確認沒有忽略其他狀況，再分析未來並決定是否繼續持有或加碼減碼。\n"
            f"在分析{task.symbol}的技術面時，請務必從以下幾個層面進行全面的評估：\n"
            "1. 趨勢與價位分析: 判斷目前股價處於長期、中期、短期分別處於何種趨勢（上升、下降、或盤整），並指出圖表上關鍵的「支撐」與「壓力」區間\n"
            "2. 技術指標分析: 分析中期、長期移動平均線（例如 20MA, 60MA, 240MA）的排列狀況，判斷市場是處於多頭或空頭排列;檢視 RSI 指標的數值，判斷市場是否處於超買 (>70) 或超賣 (<30) 狀態，並特別注意是否存在價格與指標走勢相反的「背離」現象;分析 MACD 的快慢線交叉情況與柱狀體的變化，以判斷市場動能的增強或減弱;檢視布林通道的帶寬變化，判斷市場波動性的收斂或擴張，分析股價與上、中、下三條軌道的互動關係\n"
            "3. 型態與成交量分析: 識別圖表上是否正在形成經典的價格型態，例如：頭肩頂/底、W底/M頭、旗形、或是三角收斂等，分析成交量的變化。一個健康的趨勢通常伴隨著成交量的支持（例如：價漲量增），若出現價量背離（例如：價漲量縮），則需提出警示\n"
            "綜合以上所有分析，嚴格對照下面的邏輯產出最終的「交易建議」:\n"
            "- strong_buy: 長、中、短期趨勢皆為多頭，且 RSI 無頂部背離，成交量配合價漲\n"
            "- buy: 長期多頭，中期多頭，短線回測支撐有守，長線趨勢保護\n"
            "- neutral: 長中短期趨勢不一致（例如：長期多頭但中期跌破支撐），或處於布林帶壓縮的情況\n"
            "- sell: 長期空頭，中期反彈無力\n"
            "- strong_sell: 長、中、短期趨勢皆為空頭，且 RSI 無底部背離，成交量配合價跌\n"
        ))]
    return {"messages": [_technical_llm.invoke(msgs)]}

def _technical_route(state: TechnicalSubgraphState):
    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return "technical_format"
    if any(tc["name"] == "TechnicalOutput" for tc in tool_calls):
        return "technical_format"
    return "technical_tools"

def _technical_format_node(state: TechnicalSubgraphState):
    last_msg = state["messages"][-1]
    for tc in (last_msg.tool_calls or []):
        if tc["name"] == "TechnicalOutput":
            args = tc["args"]
            analysis     = [TechnicalAnalysisReport(**r)     for r in (args.get("technical_analysis_reports")     or [])]
            verification = [TechnicalVerificationReport(**r) for r in (args.get("technical_verification_reports") or [])]
            return {
                "technical_analysis_reports":     analysis,
                "technical_verification_reports": verification,
            }
    return {"technical_analysis_reports": [], "technical_verification_reports": []}

_technical_sg = StateGraph(TechnicalSubgraphState)
_technical_sg.add_node("technical_clear", clear_messages)  # 隔離父 graph 的 messages
_technical_sg.add_node("technical_llm", _technical_llm_node)
_technical_sg.add_node("technical_tools", ToolNode(_technical_tools))
_technical_sg.add_node("technical_image_handler", _handle_image_tool_results)
_technical_sg.add_node("technical_format", _technical_format_node)
_technical_sg.add_edge(START, "technical_clear")
_technical_sg.add_edge("technical_clear", "technical_llm")
_technical_sg.add_conditional_edges("technical_llm", _technical_route, ["technical_tools", "technical_format"])
_technical_sg.add_edge("technical_tools", "technical_image_handler")
_technical_sg.add_edge("technical_image_handler", "technical_llm")
_technical_sg.add_edge("technical_format", END)
technical_agent = _technical_sg.compile()

# --- 5. News Agent Subgraph ---
class NewsSubgraphState(TypedDict):
    task: Task
    end_date: str  # 從父 AgentState 透過 key name matching 自動注入
    messages: Annotated[List[AnyMessage], add_messages]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add]

_news_llm = llm.bind_tools(_news_tools + [NewsOutput])

def _news_llm_node(state: NewsSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        task = state["task"]
        end_date = state["end_date"]
        msgs = [HumanMessage(content=(
            f"你是一位新聞分析師，主要任務是{task.task}，你的專長是從紛雜的新聞資訊中，提煉出對{task.symbol}股價有實質影響的催化劑。你負責分析非結構化的文字資訊（擴廠、新產能、新技術、新產品、產業趨勢、供應鏈等），並將其轉化為對未來股價的影響力評估\n"
            f"本次分析的資料截止日期為 {end_date}。所有工具呼叫的 end_date 參數皆必須設為 {end_date}，絕對不得使用超過此日期的任何價格或技術指標資料。\n"
            "每次呼叫 `search_news` 的 query 參數必須符合以下格式：「<股票代號或公司名稱> + 具體業務關鍵字」。\n"
            f"例如：「{task.symbol} 擴廠計畫 2025」、「{task.symbol} 新客戶訂單」、「{task.symbol} 供應鏈缺貨」、「{task.symbol} 併購案」。\n"
            f"每個 query 都必須以 {task.symbol} 的股票代號或公司名稱起頭，確保搜索結果聚焦在目標公司。\n"
            "- 針對擴張事件(含併購、擴產等): 搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：收購對象、擴建產能規模、合併條款等）; \n"
            "深入探究公司執行此擴張行動背後的戰略意圖。是為了獲取關鍵技術、擴大市佔率、進入新地理市場、消化訂單、消除競爭對手，還是為了產生規模經濟與成本協同效應？;\n"
            "評估此事件在未來 1-3 年內，可能為公司的營收、毛利率、營業利益率及每股盈餘（EPS）帶來的增長潛力。特別注意短期內是否可能因整合成本而稀釋獲利;\n"
            "判斷此次擴張是否能有效增強或拓寬公司的核心護城河（Moat），以及是否能提升公司的競爭優勢和市場地位。;\n"
            "最後需要客觀評估潛在的風險\n"
            "- 針對新產品/技術: 搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：新產品、新技術或專利的發布事件），並判斷此次創新是屬於「破壞式創新」（開創新市場）、「持續性創新」（在現有市場做得更好），還是僅為「漸進式改良」？\n"
            "分析此新產品/技術精準解決了目標客戶的哪個核心痛點？其提供的價值主張是否足夠清晰且具吸引力？\n"
            "評估該產品所瞄準的總體潛在市場、可服務市場與初期可獲得市場的規模與增長潛力。\n"
            "- 針對產業趨勢: 搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：AI PC 的崛起、GLP-1 減重藥物的普及、人形機器人的商業化），精準定義此趨勢的本質是什麼？（例如：AI算力需求爆發、電動車滲透率提升、永續能源轉型等）。\n"
            "判斷此趨勢目前處於哪個發展階段？是「萌芽期」（高風險高回報）、「成長期」（能見度高，競爭加劇）、「成熟期」（格局穩定，贏家通吃），還是「衰退期」？\n"
            "評估此趨勢是短期題材，還是將對產業產生長達一年以上的結構性改變？\n"
            "分析此趨勢將如何衝擊並重塑現有的產業價值鏈？價值將從哪個環節流出，又將集中到哪個新環節？\n"
            "在新的價值鏈中，最關鍵的瓶頸（或最稀缺的資源）是什麼？哪個環節將捕獲整個產業鏈中最大比例的利潤？（例如：在AI趨勢中，可能是GPU晶片；在電動車趨勢中，可能是電池或充電設施）。\n"
            "評估公司的業務與此趨勢的相關性有多高？\n"
            "分析公司是否已具備抓住此趨勢的技術、產能、專利或市場通路等核心競爭力與進入壁壘？\n"
            "識別與此趨勢相關的投資風險\n"
            "- 針對供應鏈狀況:搜索近期相關事件，搜索完畢後彙整並清晰描述該事件的具體內容（例如：贏得大客戶訂單、關鍵供應商變動、市場需求暴增、或出現缺貨/斷鏈的情況），評估此事件的影響是短期的還是長期的？\n"
            "預測事件對股價產生影響的可能時間範圍，是屬於短期題材發酵、中期營運整合，還是需要長期才能顯現價值，最後給出投資建議:\n"
            "- strong_buy: 擴張能顯著增強護城河或取得關鍵技術，且資金充裕。市場將重新評價估值\n"
            "- buy: 雖擴大市佔，但短期面臨整合陣痛或股權稀釋。回檔是長線佈局點\n"
            "- neutral: 影響有限。屬於維持競爭力的例行性支出，非額外利多，市場通常已反應\n"
            "- sell: 轉型豪賭（如跨界整合/高槓桿），成敗未定，建議等待財報驗證\n"
            "- strong_sell: 溢價收購或無助核心競爭力的行為，不利股東，建議避開\n"
        ))]
    return {"messages": [_news_llm.invoke(msgs)]}

def _news_route(state: NewsSubgraphState):
    tool_calls = state["messages"][-1].tool_calls
    if not tool_calls:
        return "news_format"
    if any(tc["name"] == "NewsOutput" for tc in tool_calls):
        return "news_format"
    return "news_tools"

def _news_format_node(state: NewsSubgraphState):
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

_news_sg = StateGraph(NewsSubgraphState)
_news_sg.add_node("news_clear", clear_messages)  # 隔離父 graph 的 messages
_news_sg.add_node("news_llm", _news_llm_node)
_news_sg.add_node("news_tools", ToolNode(_news_tools))
_news_sg.add_node("news_format", _news_format_node)
_news_sg.add_edge(START, "news_clear")
_news_sg.add_edge("news_clear", "news_llm")
_news_sg.add_conditional_edges("news_llm", _news_route, ["news_tools", "news_format"])
_news_sg.add_edge("news_tools", "news_llm")
_news_sg.add_edge("news_format", END)
news_agent = _news_sg.compile()

# --- 6. Critic Subgraph ---
# Critic 只處理 VerificationReport，彙整上期持股的驗證結果並提煉教訓
class CriticSubgraphState(TypedDict):
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]
    messages: Annotated[List[AnyMessage], add_messages]
    critic_reflections: Annotated[List[str], operator.add]

# _critic_llm = llm.bind_tools(_critic_tools)

def _critic_llm_node(state: CriticSubgraphState):
    # Build a clean prompt from structured VerificationReports only.
    # Never inherit messages from the parent to avoid token waste.
    reports_summary = (
        f"財務驗證報告:\n{state.get('financial_verification_reports')}\n\n"
        f"技術驗證報告:\n{state.get('technical_verification_reports')}\n\n"
        f"新聞驗證報告:\n{state.get('news_verification_reports')}"
    )
    msgs = [HumanMessage(content=(
        "你是一位投資決策系統中的事後檢討稽核員。你的職責是針對上期庫存進行歸因分析。\n"
        f"你需要整合來自 Financial, Technical, News Analyst 的驗證報告，對比當初的買入理由與實際發生的結果，找出決策成功/失敗的根本原因，並透過 {tool_names} 儲存成記憶，供未來交易參考\n"
        f"驗證報告: {reports_summary}\n"
        "分析方法:\n"
        "Step1: 事實核對\n"
        "- 情境 A： 預測發生了，股價也漲了 -> 決策正確（記錄成功模式）\n"
        "- 情境 B： 預測發生了，但股價跌了 -> 市場定價錯誤 或 忽略了其他風險（需深度檢討）\n"
        "- 情境 C： 預測沒發生（例如營收不如預期） -> 分析失準（需檢討分析邏輯）\n"
        "Step2: 偏誤識別\n"
        "- 確認偏誤： 是否只看利多新聞，忽略了當時已存在的利空訊號？\n"
        "- 過度樂觀： 是否對未實現的「轉機」給予過高權重？\n"
        "- 技術/基本面背離： 是否在基本面轉好但技術面崩盤時，執意進場接刀？\n"
        "Step3: 提煉教訓\n"
        "- 將分析結果轉化為 **通用的投資原則**，並使用 {tool_names} 儲存成記憶，供未來交易參考。例如: 當基本面出現明顯轉機但技術面尚未反應時，應該耐心等待技術指標確認轉勢後再進場，以避免過早接刀的風險。"
        "- 原則必須具體且可執行，供 Portfolio Manager 下次決策參考"
        "最後要依 股票代號、買入理由、驗證結果、學到的經驗教訓 將結果以markdown格式儲存成報告"
    ))]
    return {"messages": [llm.invoke(msgs)]}

def _critic_route(state: CriticSubgraphState):
    return "critic_tools" if state["messages"][-1].tool_calls else "critic_format"

def _critic_format_node(state: CriticSubgraphState):
    final_text = state["messages"][-1].content
    return {"critic_reflections": [final_text]}

_critic_sg = StateGraph(CriticSubgraphState)
_critic_sg.add_node("critic_llm", _critic_llm_node)
# _critic_sg.add_node("critic_tools", ToolNode(_critic_tools))
_critic_sg.add_node("critic_format", _critic_format_node)
_critic_sg.add_edge(START, "critic_llm")
_critic_sg.add_conditional_edges("critic_llm", _critic_route, ["critic_format"])
# _critic_sg.add_edge("critic_tools", "critic_llm")
_critic_sg.add_edge("critic_format", END)
critic_agent = _critic_sg.compile()

# --- 7. Portfolio Manager Subgraph ---
class PortfolioSubgraphState(TypedDict):
    user_query: str
    critic_reflections: List[str]
    messages: Annotated[List[AnyMessage], add_messages]
    # Analysis reports (新標的)
    financial_analysis_reports: List[FinancialAnalysisReport]
    technical_analysis_reports: List[TechnicalAnalysisReport]
    news_analysis_reports: List[NewsAnalysisReport]
    # Verification reports (庫存股)
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]
    portfolio_decisions: Annotated[List[PortfolioDecision], operator.add]

_portfolio_llm = llm.bind_tools([PortfolioDecisions])

def _portfolio_llm_node(state: PortfolioSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        fin_analysis   = state.get("financial_analysis_reports") or []
        tech_analysis  = state.get("technical_analysis_reports") or []
        news_analysis  = state.get("news_analysis_reports") or []
        fin_verify     = state.get("financial_verification_reports") or []
        tech_verify    = state.get("technical_verification_reports") or []
        news_verify    = state.get("news_verification_reports") or []
        critic_summary = "\n".join(state.get("critic_reflections") or [])
        msgs = [HumanMessage(content=(
            "你是擁有最終裁量權的投資長。你的工作是做出投資決策。你需要綜合考量分析師的報告、市場情況、歷史教訓，你的目標是建構一個「高勝率」且「風險可控」的投資組合。你必須具備批判性思維，當子 Agent 意見分歧時，由你進行最終裁決。\n"
            "新標的分析報告 (ANALYSIS):\n"
            f"  財務: {fin_analysis}\n"
            f"  技術: {tech_analysis}\n"
            f"  新聞: {news_analysis}\n\n"
            "庫存股驗證報告 (VERIFICATION):\n"
            f"  財務: {fin_verify}\n"
            f"  技術: {tech_verify}\n"
            f"  新聞: {news_verify}\n\n"
            f"Critic 反思教訓: {critic_summary}\n\n"
            f"使用者需求: {state['user_query']}\n"
            "決策邏輯:\n"
            "1. 根據市場情況調整對各分析師的信任權重: 例如在 Bull Market: 重視 News (題材) 與 Financial (成長)。權重範例：Fin 40% / News 40% / Tech 20%。;Bear/Choppy Market (空頭/震盪): 重視 Financial (估值保護) 與 Technical (支撐防守)。權重範例：Fin 50% / Tech 30% / News 20%。"
            "2. 訊號衝突解決: 若 Financial 評為 'Strong_Sell' (有地雷/假帳風險)，無論技術面多好，一律拒絕買進。若 Technical 評為 'Strong_Sell' (趨勢完全破壞)，除非是超長線價值投資，否則暫緩買進。\n"
            "3. 部位管理: 根據最終信心分數 (0-10) 決定動作，Score > 8: Aggressive Buy (建倉/加碼 10-15% 權重)，Score 7: Buy (建倉 5-8% 權重)，Score 5~6: Hold (觀望/續抱)。Score < 5: Sell (減碼/清倉)\n"
            "完成分析後請呼叫 PortfolioDecisions 工具回傳最終決策。\n"
        ))]
    return {"messages": [_portfolio_llm.invoke(msgs)]}

def _portfolio_route(state: PortfolioSubgraphState):
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls and any(tc["name"] == "PortfolioDecisions" for tc in tool_calls):
        return "portfolio_format"
    return "portfolio_llm"

def _portfolio_format_node(state: PortfolioSubgraphState):
    last_msg = state["messages"][-1]
    for tc in (last_msg.tool_calls or []):
        if tc["name"] == "PortfolioDecisions":
            decisions = [PortfolioDecision(**d) for d in (tc["args"].get("portfolio_decisions") or [])]
            return {"portfolio_decisions": decisions}
    return {"portfolio_decisions": []}

_portfolio_sg = StateGraph(PortfolioSubgraphState)
_portfolio_sg.add_node("portfolio_llm", _portfolio_llm_node)
_portfolio_sg.add_node("portfolio_format", _portfolio_format_node)
_portfolio_sg.add_edge(START, "portfolio_llm")
_portfolio_sg.add_conditional_edges("portfolio_llm", _portfolio_route, ["portfolio_format", "portfolio_llm"])
_portfolio_sg.add_edge("portfolio_format", END)
portfolio_manager_agent = _portfolio_sg.compile()

# ==========================================
# 4. 路由：Critic 或直接到 PM
# ==========================================
def route_after_analysts(state: AgentState) -> Literal["critic", "portfolio_manager"]:
    """若本輪有任何 VerificationReport，送往 Critic 做歸因分析；否則直接到 Portfolio Manager。"""
    has_verification = (
        bool(state.get("financial_verification_reports"))
        or bool(state.get("technical_verification_reports"))
        or bool(state.get("news_verification_reports"))
    )
    return "critic" if has_verification else "portfolio_manager"


# ==========================================
# 5. 組裝 LangGraph
# ==========================================
builder = StateGraph(AgentState)

# 加入節點
# 每個 analyst subgraph 內部已有 clear_messages 作為第一個節點，達到 message 隔離
builder.add_node("coordinator", coordinator_agent)
builder.add_node("financial_agent", financial_agent)
builder.add_node("technical_agent", technical_agent)
builder.add_node("news_agent", news_agent)
# Pass-through 節點：等待所有 analyst 完成後決定路由
builder.add_node("analysts_done", lambda state: {})
builder.add_node("critic", critic_agent)
builder.add_node("portfolio_manager", portfolio_manager_agent)

# 定義邊界 (Edges)
builder.add_edge(START, "coordinator")

# Coordinator 使用 Send API 平行派發任務給各 analyst
builder.add_conditional_edges(
    "coordinator",
    route_tasks,
    ["financial_agent", "technical_agent", "news_agent"]
)

# 所有 Analyst 節點執行完畢後，匯聚到 analysts_done
builder.add_edge("financial_agent", "analysts_done")
builder.add_edge("technical_agent", "analysts_done")
builder.add_edge("news_agent", "analysts_done")

# 依據是否有 VerificationReport 路由到 Critic 或直接到 Portfolio Manager
builder.add_conditional_edges(
    "analysts_done",
    route_after_analysts,
    ["critic", "portfolio_manager"]
)

# Critic 到 PM，最後結束
builder.add_edge("critic", "portfolio_manager")
builder.add_edge("portfolio_manager", END)

# 編譯
graph = builder.compile()

# ==========================================
# 5. 測試執行
# ==========================================
# if __name__ == "__main__":
#     initial_state = {
#         "user_query": "幫我評估台積電 (2330) 與聯發科 (2454) 是否值得買進。",
#     }
    
#     print("🚀 啟動 LangGraph Multi-Agent 系統...")
#     final_state = graph.invoke(initial_state)
    
#     print("\n✅ === 最終投資組合決策 ===")
#     for decision in final_state["portfolio_decisions"]:
#         print(f"[{decision.symbol}] 動作: {decision.action.upper()} | 權重: {decision.position*100}%")
#         print(f"原因: {decision.rationale}\n")