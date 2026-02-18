# TradingAgents/graph/setup.py

from typing import Dict
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from tradingagents.agents import (
    AgentState,
    create_coordinator,
    create_critic,
    create_fundamentals_analyst,
    create_technical_analyst,
    create_news_analyst,
    create_portfolio_manager,
)


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm

    def setup_graph(self, selected_analysts=None):
        """Set up and compile the README-aligned workflow graph."""
        coordinator_node = create_coordinator(self.deep_thinking_llm)
        fundamental_node = create_fundamentals_analyst(self.quick_thinking_llm)
        technical_node = create_technical_analyst(self.quick_thinking_llm)
        news_node = create_news_analyst(self.quick_thinking_llm)
        critic_node = create_critic(self.deep_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(self.deep_thinking_llm)

        workflow = StateGraph(AgentState)

        workflow.add_node("Coordinator", coordinator_node)
        workflow.add_node("Fundamental Analyst", fundamental_node)
        workflow.add_node("Technical Analyst", technical_node)
        workflow.add_node("News Analyst", news_node)
        workflow.add_node("Critic", critic_node)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        workflow.add_edge(START, "Coordinator")

        # Parallel fan-out from coordinator
        workflow.add_edge("Coordinator", "Fundamental Analyst")
        workflow.add_edge("Coordinator", "Technical Analyst")
        workflow.add_edge("Coordinator", "News Analyst")

        # Fan-in to critic after all analyst branches complete
        workflow.add_edge("Fundamental Analyst", "Critic")
        workflow.add_edge("Technical Analyst", "Critic")
        workflow.add_edge("News Analyst", "Critic")

        workflow.add_edge("Critic", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", END)

        return workflow.compile()
