from typing import Annotated, Any, Dict, List
from langgraph.graph import MessagesState
from .agent_output_formats import Task, FinancialAnalysisReport, FinancialVerificationReport



class FinancialState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this financial analyst"]
    financial_analysis_reports: Annotated[List[Dict[str, Any]], "Financial analyst outputs for analysis"]
    financial_verification_reports: Annotated[List[str], "Financial analyst reflections for verification"]

class TechnicalState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this technical analyst"]
    technical_analysis_reports: Annotated[List[Dict[str, Any]], "Technical analyst outputs for analysis"]
    technical_verification_reports: Annotated[List[str], "Technical analyst reflections for verification"]

class NewsState(MessagesState):
    task: Annotated[Task, "The specific task assigned to this news analyst"]
    news_analysis_reports: Annotated[List[Dict[str, Any]], "News analyst outputs for analysis"]
    news_verification_reports: Annotated[List[str], "News analyst reflections for verification"]

class AgentState(MessagesState):
    mode: Annotated[str, "Operation mode: query or strategy"]
    market_situation: Annotated[str, "Current market situation"]
    end_time: Annotated[str, "End time for the data usage and trading decision"]

    strategy: Annotated[str, "Investment strategy to follow, e.g. monthly_revenue_growth_roe"]

    technical_tasks: Annotated[List[Task], "List of technical analysis tasks to perform"]
    financial_tasks: Annotated[List[Task], "List of financial analysis tasks to perform"]
    news_tasks: Annotated[List[Task], "List of news analysis tasks to perform"]

    financial_analysis_reports: Annotated[List[FinancialAnalysisReport], "Financial analyst outputs for analysis"]
    financial_verification_reports: Annotated[List[FinancialVerificationReport], "Financial analyst reflections for verification"]
    technical_analysis_reports: Annotated[List[Dict[str, Any]], "Technical analyst outputs  for analysis"]
    technical_verification_reports: Annotated[List[str], "Technical analyst reflections for verification"]
    news_analysis_reports: Annotated[List[Dict[str, Any]], "News analyst outputs  for analysis"]
    news_verification_reports: Annotated[List[str], "News analyst reflections for verification"]
    
    critic_reflections: Annotated[List[str], "Critic reflections for verification"]
    portfolio_decision: Annotated[Dict[str, Any], "Portfolio manager final descision for the trade on the next trading day"]

    market_report: Annotated[str, "Serialized technical report"]
    news_report: Annotated[str, "Serialized news report"]
    financials_report: Annotated[str, "Serialized financial report"]
    sentiment_report: Annotated[str, "Reserved for compatibility"]
    investment_plan: Annotated[str, "Reserved for compatibility"]
    trader_investment_plan: Annotated[str, "Reserved for compatibility"]
    final_trade_decision: Annotated[str, "Final decision JSON string"]
