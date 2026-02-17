# TradingAgents/graph/propagation.py

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, company_name: str, trade_date: str, user_request: str = "", run_id: str = ""
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph."""
        request = user_request or company_name
        rid = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return {
            "messages": [("human", company_name)],
            "run_id": rid,
            "user_request": request,
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "mode": "single",
            "market_regime": "Neutral",
            "coordinator_plan": {},
            "financial_reports": [],
            "technical_reports": [],
            "news_reports": [],
            "critic_reflections": [],
            "portfolio_decision": {},
            "market_report": "",
            "fundamentals_report": "",
            "sentiment_report": "",
            "news_report": "",
            "investment_plan": "",
            "trader_investment_plan": "",
            "final_trade_decision": "",
        }

    def get_graph_args(self, callbacks: Optional[List] = None) -> Dict[str, Any]:
        """Get arguments for the graph invocation.

        Args:
            callbacks: Optional list of callback handlers for tool execution tracking.
                       Note: LLM callbacks are handled separately via LLM constructor.
        """
        config = {"recursion_limit": self.max_recur_limit}
        if callbacks:
            config["callbacks"] = callbacks
        return {
            "stream_mode": "values",
            "config": config,
        }
