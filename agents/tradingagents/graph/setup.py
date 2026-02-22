# TradingAgents/graph/setup.py

from typing import Dict
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    AgentState,
    FinancialState,
    TechnicalState,
    NewsState,
    create_coordinator,
    create_critic,
    create_financial_analyst,
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
        tool_nodes: Dict[str, ToolNode],
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes

    def setup_graph(self):
        """Set up and compile the workflow graph."""
        coordinator_node = create_coordinator(self.deep_thinking_llm)
        financial_analyst_node = create_financial_analyst(self.quick_thinking_llm)
        technical_analyst_node = create_technical_analyst(self.quick_thinking_llm)
        news_analyst_node = create_news_analyst(self.quick_thinking_llm)
        critic_node = create_critic(self.deep_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(self.deep_thinking_llm)

        workflow = StateGraph(AgentState)

        workflow.add_node("Coordinator", coordinator_node)
        workflow.add_node("Financial Analyst", financial_analyst_node)
        workflow.add_node("Technical Analyst", technical_analyst_node)
        workflow.add_node("News Analyst", news_analyst_node)
        workflow.add_node("Critic", critic_node)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        for agent_name, tool_node in self.tool_nodes.items():
            workflow.add_node(f"tools_{agent_name}", tool_node)

        workflow.add_edge(START, "Coordinator")

        # Parallel fan-out from coordinator
        workflow.add_edge("Coordinator", "Financial Analyst")
        workflow.add_edge("Coordinator", "Technical Analyst")
        workflow.add_edge("Coordinator", "News Analyst")

        # Fan-in to critic after all analyst branches complete
        workflow.add_edge("Financial Analyst", "Critic")
        workflow.add_edge("Technical Analyst", "Critic")
        workflow.add_edge("News Analyst", "Critic")

        workflow.add_edge("Critic", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", END)

        return workflow.compile()
