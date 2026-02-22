from typing import Annotated, Any, Dict, List
from langgraph.graph import MessagesState
from .agent_output_formats import *



class FinancialState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this financial analyst"]
    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], "Financial analyst outputs for analysis"]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], "Financial analyst reflections for verification"]

class TechnicalState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this technical analyst"]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], "Technical analyst outputs for analysis"]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], "Technical analyst reflections for verification"]

class NewsState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this news analyst"]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], "News analyst outputs for analysis"]
    news_verification_reports: Annotated[List[NewsVerificationReport], "News analyst reflections for verification"]

class AgentState(MessagesState):
    user_query: Annotated[str, "The original user query that initiated the analysis and trading process"]
    mode: Annotated[str, "Operation mode: query or strategy"]
    market_situation: Annotated[str, "Current market situation"]
    end_time: Annotated[str, "End time for the data usage and trading decision"]

    strategy: Annotated[str, "Investment strategy to follow, e.g. monthly_revenue_growth_roe"]

    technical_tasks: Annotated[List[Task], "List of technical analysis tasks to perform"]
    financial_tasks: Annotated[List[Task], "List of financial analysis tasks to perform"]
    news_tasks: Annotated[List[Task], "List of news analysis tasks to perform"]

    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], "Financial analyst outputs for analysis"]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], "Financial analyst reflections for verification"]
    technical_analysis_reports: Annotated[List[TechnicalAnalysisReport], "Technical analyst outputs  for analysis"]
    technical_verification_reports: Annotated[List[TechnicalVerificationReport], "Technical analyst reflections for verification"]
    news_analysis_reports: Annotated[List[NewsAnalysisReport], "News analyst outputs  for analysis"]
    news_verification_reports: Annotated[List[NewsVerificationReport], "News analyst reflections for verification"]
    
    critic_reflections: Annotated[List[str], "Critic reflections for verification"]
    portfolio_decisions: Annotated[List[PortfolioDecisions], "Portfolio manager final decisions for the trade on the next trading day"]

