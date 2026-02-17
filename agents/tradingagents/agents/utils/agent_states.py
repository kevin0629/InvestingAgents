from typing import Annotated, Any, Dict, List
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    user_request: Annotated[str, "Raw user request for coordinator"]
    company_of_interest: Annotated[str, "Primary ticker/company query"]
    trade_date: Annotated[str, "Trade date (YYYY-MM-DD)"]
    mode: Annotated[str, "single or batch"]
    market_regime: Annotated[str, "Current market regime summary"]
    coordinator_plan: Annotated[Dict[str, Any], "Coordinator output JSON"]

    financial_reports: Annotated[List[Dict[str, Any]], "Financial analyst outputs"]
    technical_reports: Annotated[List[Dict[str, Any]], "Technical analyst outputs"]
    news_reports: Annotated[List[Dict[str, Any]], "News analyst outputs"]
    critic_reflections: Annotated[List[Dict[str, Any]], "Critic reflections for verification"]
    portfolio_decision: Annotated[Dict[str, Any], "Portfolio manager final JSON"]

    market_report: Annotated[str, "Serialized technical report"]
    news_report: Annotated[str, "Serialized news report"]
    fundamentals_report: Annotated[str, "Serialized financial report"]
    sentiment_report: Annotated[str, "Reserved for compatibility"]
    investment_plan: Annotated[str, "Reserved for compatibility"]
    trader_investment_plan: Annotated[str, "Reserved for compatibility"]
    final_trade_decision: Annotated[str, "Final decision JSON string"]
