import operator
from typing import Annotated, Any, Dict, List
from langgraph.graph import MessagesState
from .agent_output_formats import *



class FinancialState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this financial analyst"]
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add, "Financial analyst outputs for analysis"]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add, "Financial analyst reflections for verification"]

class TechnicalState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this technical analyst"]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add, "Technical analyst outputs for analysis"]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add, "Technical analyst reflections for verification"]

class NewsState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this news analyst"]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add, "News analyst outputs for analysis"]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add, "News analyst reflections for verification"]

class AgentState(MessagesState):
    user_query: Annotated[str, "The original user query that initiated the analysis and trading process"]
    mode: Annotated[str, "Operation mode: query or strategy"]
    market_situation: Annotated[str, "Current market situation"]
    end_date: Annotated[str, "End time for the data usage and trading decision"]

    strategy: Annotated[str, "Investment strategy to follow, e.g. monthly_revenue_growth_roe"]

    technical_tasks: Annotated[List[Task], operator.add, "List of technical analysis tasks to perform"]
    financial_tasks: Annotated[List[Task], operator.add, "List of financial analysis tasks to perform"]
    news_tasks: Annotated[List[Task], operator.add, "List of news analysis tasks to perform"]

    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], operator.add, "Financial analyst outputs for analysis"]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], operator.add, "Financial analyst reflections for verification"]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], operator.add, "Technical analyst outputs  for analysis"]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], operator.add, "Technical analyst reflections for verification"]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], operator.add, "News analyst outputs  for analysis"]
    news_verification_reports: Annotated[List[NewsVerificationReport], operator.add, "News analyst reflections for verification"]
    
    critic_reflections: Annotated[List[str], operator.add, "Critic reflections for verification"]
    portfolio_decisions: Annotated[List[PortfolioDecisions], operator.add, "Portfolio manager final decisions for the trade on the next trading day"]

