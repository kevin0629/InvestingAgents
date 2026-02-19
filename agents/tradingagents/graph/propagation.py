# TradingAgents/graph/propagation.py

from typing import Dict, Any, List, Optional


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(self, user_request: str) -> Dict[str, Any]:
        """Create the initial state for the agent graph."""
        return {
            "user_request": user_request,
            "coordinator_plan": {},
            "financial_reports": [],
            "technical_reports": [],
            "news_reports": [],
            "critic_reflections": [],
            "portfolio_decision": {},
            "technical_report": "",
            "fundamental_report": "",
            "news_report": "",
            "investment_plan": "",
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
