import os
import operator
from typing import Annotated, List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
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
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # langgraph dev loads .env automatically via langgraph.json

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

# ==========================================
# 1. Pydantic Models & State 定義 (簡化版，對齊你的設計)
# ==========================================

class Task(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this task, must be integer string like '2330', '2455', '3491'")
    task_type: Literal["ANALYSIS", "VERIFICATION"] = Field(None, description="Type of the technical task")
    task: str = Field(None, description="Detailed description of the task")
    buy_reason: str = Field(None, description="The reason for recommending a buy action, if task_type is VERIFICATION else None")

class CoordinatorOutput(BaseModel):
    """Respond to the user with this"""
    user_query: str = Field(None, description="The original user query that initiated the analysis and trading process")
    mode: Literal["query", "strategy"] = Field(None, description="Operation mode: query or strategy")
    market_situation: str = Field(None, description="Summary of the current market situation.")
    end_date: str = Field(None, description="The end date for the data retrieval, analysis and trading decision.")
    
    strategy: str = Field(None, description="The investment strategy to follow, e.g. monthly_revenue_growth_roe.")

    technical_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for technical analysis.")
    financial_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for financial analysis.")
    news_tasks: List[Task] = Field(None, description="The coordinator's detailed plan for news analysis.")



class FinancialAnalysisReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this financial analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the financial analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(None, description="Detailed financial analysis report for the given stock symbol")

class FinancialVerificationReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this financial verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the financial analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(None, description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(None, description="The financial analyst's reflection and review comment for the buy_reason")
    report: str = Field(None, description="The result of the verification process for the given financial task")

class FinancialOutput(BaseModel):
    """Respond to the user with financial_analysis_reports when the task_type is ANALYSIS, or financial_verification_reports when the task_type is VERIFICATION"""
    financial_analysis_reports: List[FinancialAnalysisReport] = Field(None, description="Financial analyst outputs for analysis")
    financial_verification_reports: List[FinancialVerificationReport] = Field(None, description="Financial analyst reflections for verification")



class NewsAnalysisReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this news analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the news analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(None, description="Detailed news analysis report for the given stock symbol")

class NewsVerificationReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this news verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the news analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(None, description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(None, description="The news analyst's reflection and review comment for the buy_reason")
    report: str = Field(None, description="The result of the verification process for the given news task")

class NewsOutput(BaseModel):
    """Respond to the user with news_analysis_reports when the task_type is ANALYSIS, or news_verification_reports when the task_type is VERIFICATION"""
    news_analysis_reports: List[NewsAnalysisReport] = Field(None, description="News analyst outputs for analysis")
    news_verification_reports: List[NewsVerificationReport] = Field(None, description="News analyst reflections for verification")


class TechnicalAnalysisReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this technical analysis report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the technical analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    report: str = Field(None, description="Detailed technical analysis report for the given stock symbol")

class TechnicalVerificationReport(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this technical verification report")
    signal: Literal["strong_buy", "buy", "neutral", "sell", "strong_sell"] = Field(None, description="Investment recommendation based on the technical analysis")
    confidence_score: int = Field(None, description="Confidence score for the investment recommendation, ranging from 0 to 10")
    buy_reason: str = Field(None, description="The reason for recommending a buy action, if applicable")
    review_comment: str = Field(None, description="The technical analyst's reflection and review comment for the buy_reason")
    report: str = Field(None, description="The result of the verification process for the given technical task")

class TechnicalOutput(BaseModel):
    """Respond to the user with technical_analysis_reports when the task_type is ANALYSIS, or technical_verification_reports when the task_type is VERIFICATION"""
    technical_analysis_reports: List[TechnicalAnalysisReport] = Field(None, description="Technical analyst outputs for analysis")
    technical_verification_reports: List[TechnicalVerificationReport] = Field(None, description="Technical analyst reflections for verification")


class PortfolioDecision(BaseModel):
    symbol: str = Field(None, description="The stock symbol related to this portfolio decision")
    action: Literal["buy", "hold", "sell"] = Field(None, description="The trading action decided by the portfolio manager for the next trading day")
    position: float = Field(None, description="The target position size for the given stock symbol, represented as a percentage of the total portfolio (e.g., 0.1 for 10%)")
    confidence_score: int = Field(None, description="Confidence score for the trading action, ranging from 0 to 10")
    rationale: str = Field(None, description="Detailed rationale behind the portfolio manager's trading decision for the given stock symbol")

class PortfolioDecisions(BaseModel):
    """Respond to the user with this"""
    portfolio_decisions: List[PortfolioDecision] = Field(None, description="The portfolio manager's final trading decisions for the next trading day")



class FinancialState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this financial analyst"]
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add]

class TechnicalState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this technical analyst"]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add]

class NewsState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this news analyst"]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add]

class AgentState(MessagesState):
    user_query: Annotated[str, "The original user query that initiated the analysis and trading process"]
    mode: Annotated[str, "Operation mode: query or strategy"]
    market_situation: Annotated[str, "Current market situation"]
    end_date: Annotated[str, "End time for the data usage and trading decision"]

    strategy: Annotated[str, "Investment strategy to follow, e.g. monthly_revenue_growth_roe"]

    financial_messages: Annotated[List[AnyMessage], add_messages]
    technical_messages: Annotated[List[AnyMessage], add_messages]
    news_messages: Annotated[List[AnyMessage], add_messages]
    portfolio_messages: Annotated[List[AnyMessage], add_messages]

    technical_tasks: Annotated[List[Task], operator.add]
    financial_tasks: Annotated[List[Task], operator.add]
    news_tasks: Annotated[List[Task], operator.add]

    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add]
    
    critic_reflections: Annotated[List[str], operator.add]
    portfolio_decisions: Annotated[List[PortfolioDecision], operator.add]

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
    messages: Annotated[List[AnyMessage], add_messages]
    financial_tasks: Annotated[List[Task], operator.add]
    technical_tasks: Annotated[List[Task], operator.add]
    news_tasks: Annotated[List[Task], operator.add]

_coordinator_llm = llm.bind_tools(_coordinator_tools)

def _coordinator_llm_node(state: CoordinatorSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        msgs = [HumanMessage(content=(
            "你是量化策略經理。請先用工具查詢大盤情況與相關新聞，"
            "再為財務、技術、新聞部門生成對應的分析任務。\n"
            f"使用者需求: {state['user_query']}。\n"
            "若使用有給策略，請使用 get_backtest_report 工具查詢策略的歷史表現，並進一步篩選策略選出的股票\n"
            "如果使用者有給資料截止日期，使用工具取得的資料必須不超過該日期\n"
        ))]
    return {"messages": [_coordinator_llm.invoke(msgs)]}

def _coordinator_route(state: CoordinatorSubgraphState):
    return "coordinator_tools" if state["messages"][-1].tool_calls else "coordinator_format"

def _extract_text(content) -> str:
    """Safely extract text from a message content that may be a str or list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            # skip image_url blocks
        return " ".join(parts)
    return str(content)


def _coordinator_format_node(state: CoordinatorSubgraphState):
    all_content = "\n".join(
        _extract_text(m.content) for m in state["messages"]
        if hasattr(m, "content") and m.content
    )
    result = llm.with_structured_output(CoordinatorOutput).invoke(
        f"根據以下對話，為財務、技術、新聞部門生成對應的分析任務清單。\n"
        f"使用者需求: {state['user_query']}\n\n{all_content}"
    )
    return {
        "financial_tasks": result.financial_tasks or [],
        "technical_tasks": result.technical_tasks or [],
        "news_tasks": result.news_tasks or [],
    }

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
    sends = []
    for task in state.get("financial_tasks", []):
        sends.append(Send("financial_agent", {"task": task}))
    for task in state.get("technical_tasks", []):
        sends.append(Send("technical_agent", {"task": task}))
    for task in state.get("news_tasks", []):
        sends.append(Send("news_agent", {"task": task}))
    return sends

# --- 3. Financial Agent Subgraph ---
class FinancialSubgraphState(TypedDict):
    task: Task
    messages: Annotated[List[AnyMessage], add_messages]
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add]

_financial_llm = llm.bind_tools(_financial_tools)

def _financial_llm_node(state: FinancialSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        task = state["task"]
        msgs = [HumanMessage(content=f"你是頂尖財務分析師，請使用工具查資料並給出分析結論。\n任務: {task.task}\n股票: {task.symbol}")]
    return {"messages": [_financial_llm.invoke(msgs)]}

def _financial_route(state: FinancialSubgraphState):
    return "financial_tools" if state["messages"][-1].tool_calls else "financial_format"

def _financial_format_node(state: FinancialSubgraphState):
    task = state["task"]
    final_text = state["messages"][-1].content
    report = llm.with_structured_output(FinancialAnalysisReport).invoke(
        f"請將以下分析轉為 JSON 格式: {final_text}\n記得附上 symbol {task.symbol}"
    )
    return {"financial_analysis_reports": [report]}

_financial_sg = StateGraph(FinancialSubgraphState)
_financial_sg.add_node("financial_llm", _financial_llm_node)
_financial_sg.add_node("financial_tools", ToolNode(_financial_tools))
_financial_sg.add_node("financial_image_handler", _handle_image_tool_results)
_financial_sg.add_node("financial_format", _financial_format_node)
_financial_sg.add_edge(START, "financial_llm")
_financial_sg.add_conditional_edges("financial_llm", _financial_route, ["financial_tools", "financial_format"])
_financial_sg.add_edge("financial_tools", "financial_image_handler")
_financial_sg.add_edge("financial_image_handler", "financial_llm")
_financial_sg.add_edge("financial_format", END)
financial_agent = _financial_sg.compile()

# --- 4. Technical Agent Subgraph ---
class TechnicalSubgraphState(TypedDict):
    task: Task
    messages: Annotated[List[AnyMessage], add_messages]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add]

_technical_llm = llm.bind_tools(_technical_tools)

def _technical_llm_node(state: TechnicalSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        task = state["task"]
        msgs = [HumanMessage(content=f"你是技術分析師，請使用工具查資料並給出分析結論。\n任務: {task.task}\n股票: {task.symbol}")]
    return {"messages": [_technical_llm.invoke(msgs)]}

def _technical_route(state: TechnicalSubgraphState):
    return "technical_tools" if state["messages"][-1].tool_calls else "technical_format"

def _technical_format_node(state: TechnicalSubgraphState):
    task = state["task"]
    final_text = state["messages"][-1].content
    report = llm.with_structured_output(TechnicalAnalysisReport).invoke(
        f"請將以下分析轉為 JSON 格式: {final_text}\n記得附上 symbol {task.symbol}"
    )
    return {"technical_analysis_reports": [report]}

_technical_sg = StateGraph(TechnicalSubgraphState)
_technical_sg.add_node("technical_llm", _technical_llm_node)
_technical_sg.add_node("technical_tools", ToolNode(_technical_tools))
_technical_sg.add_node("technical_image_handler", _handle_image_tool_results)
_technical_sg.add_node("technical_format", _technical_format_node)
_technical_sg.add_edge(START, "technical_llm")
_technical_sg.add_conditional_edges("technical_llm", _technical_route, ["technical_tools", "technical_format"])
_technical_sg.add_edge("technical_tools", "technical_image_handler")
_technical_sg.add_edge("technical_image_handler", "technical_llm")
_technical_sg.add_edge("technical_format", END)
technical_agent = _technical_sg.compile()

# --- 5. News Agent Subgraph ---
class NewsSubgraphState(TypedDict):
    task: Task
    messages: Annotated[List[AnyMessage], add_messages]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add]

_news_llm = llm.bind_tools(_news_tools)

def _news_llm_node(state: NewsSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        task = state["task"]
        msgs = [HumanMessage(content=f"你是新聞情緒分析師，請使用工具查資料並給出分析結論。\n任務: {task.task}\n股票: {task.symbol}")]
    return {"messages": [_news_llm.invoke(msgs)]}

def _news_route(state: NewsSubgraphState):
    return "news_tools" if state["messages"][-1].tool_calls else "news_format"

def _news_format_node(state: NewsSubgraphState):
    task = state["task"]
    final_text = state["messages"][-1].content
    report = llm.with_structured_output(NewsAnalysisReport).invoke(
        f"請將以下分析轉為 JSON 格式: {final_text}\n記得附上 symbol {task.symbol}"
    )
    return {"news_analysis_reports": [report]}

_news_sg = StateGraph(NewsSubgraphState)
_news_sg.add_node("news_llm", _news_llm_node)
_news_sg.add_node("news_tools", ToolNode(_news_tools))
_news_sg.add_node("news_format", _news_format_node)
_news_sg.add_edge(START, "news_llm")
_news_sg.add_conditional_edges("news_llm", _news_route, ["news_tools", "news_format"])
_news_sg.add_edge("news_tools", "news_llm")
_news_sg.add_edge("news_format", END)
news_agent = _news_sg.compile()

# --- 6. Critic Subgraph ---
class CriticSubgraphState(TypedDict):
    financial_analysis_reports: List[FinancialAnalysisReport]
    technical_analysis_reports: List[TechnicalAnalysisReport]
    news_analysis_reports: List[NewsAnalysisReport]
    messages: Annotated[List[AnyMessage], add_messages]
    critic_reflections: Annotated[List[str], operator.add]

# _critic_llm = llm.bind_tools(_critic_tools)

def _critic_llm_node(state: CriticSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        reports_summary = (
            f"財務分析: {state.get('financial_analysis_reports')}\n"
            f"技術分析: {state.get('technical_analysis_reports')}\n"
            f"新聞分析: {state.get('news_analysis_reports')}"
        )
        msgs = [HumanMessage(content=(
            "你是嚴格的風險控制員。請審視以下三部門報告，"
            "找出潛在矛盾，並給出最終市場評估指引。可列用工具儲存重要反思。\n"
            f"{reports_summary}"
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
    portfolio_decisions: Annotated[List[PortfolioDecision], operator.add]

class PMOutput(BaseModel):
    decisions: List[PortfolioDecision]

def _portfolio_llm_node(state: PortfolioSubgraphState):
    msgs = state.get("messages") or []
    if not msgs:
        critic_summary = "\n".join(state.get("critic_reflections") or [])
        msgs = [HumanMessage(content=(
            "你是基金經理人。請根據 Critic 的反思與使用者原始需求，"
            "決定最終的交易動作與資金權重。\n"
            f"使用者需求: {state['user_query']}\nCritic建議: {critic_summary}"
        ))]
    return {"messages": [llm.invoke(msgs)]}

def _portfolio_format_node(state: PortfolioSubgraphState):
    critic_summary = "\n".join(state.get("critic_reflections") or [])
    final_text = state["messages"][-1].content
    result = llm.with_structured_output(PMOutput).invoke(
        f"根據以下分析，生成投資組合決策。\n"
        f"使用者需求: {state['user_query']}\nCritic建議: {critic_summary}\n分析: {final_text}"
    )
    return {"portfolio_decisions": result.decisions or []}

_portfolio_sg = StateGraph(PortfolioSubgraphState)
_portfolio_sg.add_node("portfolio_llm", _portfolio_llm_node)
_portfolio_sg.add_node("portfolio_format", _portfolio_format_node)
_portfolio_sg.add_edge(START, "portfolio_llm")
_portfolio_sg.add_edge("portfolio_llm", "portfolio_format")
_portfolio_sg.add_edge("portfolio_format", END)
portfolio_manager_agent = _portfolio_sg.compile()

# ==========================================
# 4. 組裝 LangGraph
# ==========================================
builder = StateGraph(AgentState)

# 加入節點
builder.add_node("coordinator", coordinator_agent)
builder.add_node("financial_agent", financial_agent)
builder.add_node("technical_agent", technical_agent)
builder.add_node("news_agent", news_agent)
builder.add_node("critic", critic_agent)
builder.add_node("portfolio_manager", portfolio_manager_agent)

# 定義邊界 (Edges)
builder.add_edge(START, "coordinator")

# Coordinator 使用 conditional_edges (Send API) 平行發送任務
builder.add_conditional_edges(
    "coordinator",
    route_tasks,
    ["financial_agent", "technical_agent", "news_agent"]
)

# 所有 Analyst 節點執行完畢後，匯聚到 Critic
builder.add_edge("financial_agent", "critic")
builder.add_edge("technical_agent", "critic")
builder.add_edge("news_agent", "critic")

# Critic 到 PM，最後結束
builder.add_edge("critic", "portfolio_manager")
builder.add_edge("portfolio_manager", END)

# 編譯
graph = builder.compile()

# ==========================================
# 5. 測試執行
# ==========================================
if __name__ == "__main__":
    initial_state = {
        "user_query": "幫我評估台積電 (2330) 與聯發科 (2454) 是否值得買進。",
    }
    
    print("🚀 啟動 LangGraph Multi-Agent 系統...")
    final_state = graph.invoke(initial_state)
    
    print("\n✅ === 最終投資組合決策 ===")
    for decision in final_state["portfolio_decisions"]:
        print(f"[{decision.symbol}] 動作: {decision.action.upper()} | 權重: {decision.position*100}%")
        print(f"原因: {decision.rationale}\n")