import operator
from typing import Annotated, Any, Dict, List
from langgraph.graph import MessagesState
from .agent_output_formats import *


def _last_value(a, b):
    """Reducer: 並行節點同時回寫同一欄位時，取最後一個非空值（值應相同）。"""
    return b if b else a


class CoordinatorState(MessagesState):
    # user_query: str
    # mode: str
    # market_situation: str
    end_date: str
    strategy: str
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
    market_situation: str
    macro_analysis_report: 


class CriticState(MessagesState):
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]
    critic_reflections: Annotated[List[str], operator.add]

class PortfolioState(MessagesState):
    user_query: str
    mode: str
    market_situation: str
    end_date: str
    strategy: str
    critic_reflections: List[str]
    # Analysis reports（新標的）
    financial_analysis_reports: List[FinancialAnalysisReport]
    technical_analysis_reports: List[TechnicalAnalysisReport]
    news_analysis_reports: List[NewsAnalysisReport]
    # Verification reports（庫存股）
    financial_verification_reports: List[FinancialVerificationReport]
    technical_verification_reports: List[TechnicalVerificationReport]
    news_verification_reports: List[NewsVerificationReport]
    portfolio_decisions: Annotated[List[PortfolioDecision], operator.add]

class AgentState(MessagesState):
    # user_query: Annotated[str, "The original user query that initiated the analysis and trading process"]
    # mode: Annotated[str, "Operation mode: query or strategy"]
    market_situation: Annotated[str, "Current market situation"]
    end_date: Annotated[str, _last_value]

    strategy: Annotated[str, "Investment strategy to follow, e.g. monthly_revenue_growth_roe"]

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

