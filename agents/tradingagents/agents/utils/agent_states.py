import operator
from typing import Annotated, Any, Dict, List
from langgraph.graph import MessagesState
from .agent_output_formats import *


def _last_value(a, b):
    """Reducer: 並行節點同時回寫同一欄位時，取最後一個非空值（值應相同）。"""
    return b if b else a


class DistributorState(MessagesState):
    end_date: str
    strategy: str
    pre_market_performance: str
    pre_strategy_performance: str
    pre_performance: str
    previous_position_map: Dict[str, float]
    previous_stock_return_map: Dict[str, str]
    previous_holdings_context: List[Dict[str, Any]]
    financial_tasks: Annotated[List[Task], operator.add]
    technical_tasks: Annotated[List[Task], operator.add]
    news_tasks: Annotated[List[Task], operator.add]

class FinancialState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this financial analyst"]
    end_date: str
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add]

class TechnicalState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this technical analyst"]
    end_date: str
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add]

class NewsState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this news analyst"]
    end_date: str
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add]


class MacroState(MessagesState):
    end_date: str
    macro_analysis_report: MacroAnalysisReport


class CriticState(MessagesState):
    strategy: str
    end_date: str
    previous_position_map: Dict[str, float]
    previous_stock_return_map: Dict[str, str]
    previous_holdings_context: List[Dict[str, Any]]
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]
    macro_analysis_report: MacroAnalysisReport
    pre_market_performance: str
    pre_strategy_performance: str
    pre_performance: str
    critic_reflections: Annotated[List[str], operator.add]

class PortfolioState(MessagesState):
    strategy: str
    end_date: str
    # Analysis reports（新標的）
    financial_analysis_reports: List[FinancialAnalysisReport]
    technical_analysis_reports: List[TechnicalAnalysisReport]
    news_analysis_reports: List[NewsAnalysisReport]
    macro_analysis_report: MacroAnalysisReport
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]

class AgentState(MessagesState):
    strategy: Annotated[str, "Investment strategy to follow, e.g. monthly_revenue_growth_roe"]
    end_date: Annotated[str, _last_value]
    pre_market_performance: Annotated[str, _last_value]
    pre_strategy_performance: Annotated[str, _last_value]
    pre_performance: Annotated[str, _last_value]
    previous_position_map: Annotated[Dict[str, float], _last_value]
    previous_stock_return_map: Annotated[Dict[str, str], _last_value]
    previous_holdings_context: Annotated[List[Dict[str, Any]], _last_value]

    technical_tasks: Annotated[List[Task], operator.add]
    financial_tasks: Annotated[List[Task], operator.add]
    news_tasks: Annotated[List[Task], operator.add]
    
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add]
    macro_analysis_report: MacroAnalysisReport
    
    critic_reflections: Annotated[List[str], operator.add]
    portfolio_decisions: Annotated[List[PortfolioDecision], operator.add]

