# TradingAgents/graph/setup.py

from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
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

    def _has_tool_calls(self, state: Dict[str, Any]) -> bool:
        messages = state.get("messages") or []
        if not messages:
            return False
        last_message = messages[-1]
        return bool(getattr(last_message, "tool_calls", None))

    def _resolve_tool_node_name(self, *keys: str) -> str | None:
        for key in keys:
            if key in self.tool_nodes:
                return f"tools_{key}"
        return None

    def _assign_analyst_workers(self, state: AgentState) -> List[Send]:
        sends: List[Send] = []

        def _task_has_symbol(task: Any) -> bool:
            if task is None:
                return False
            if isinstance(task, dict):
                return bool(task.get("symbol"))
            return bool(getattr(task, "symbol", None))

        for task in state.get("financial_tasks") or []:
            if _task_has_symbol(task):
                sends.append(Send("Financial Analyst", {"financial_task": task}))

        for task in state.get("technical_tasks") or []:
            if _task_has_symbol(task):
                sends.append(Send("Technical Analyst", {"technical_task": task}))

        for task in state.get("news_tasks") or []:
            if _task_has_symbol(task):
                sends.append(Send("News Analyst", {"news_task": task}))

        if not sends:
            sends.append(Send("Analysis Gate", {}))

        return sends

    def _route_from_coordinator(self, state: AgentState):
        coordinator_tools_node = self._resolve_tool_node_name("coordinator")
        if coordinator_tools_node and self._has_tool_calls(state):
            return coordinator_tools_node
        return self._assign_analyst_workers(state)

    def _route_financial(self, state: AgentState) -> str:
        financial_tools_node = self._resolve_tool_node_name("financial", "fundamental")
        if financial_tools_node and self._has_tool_calls(state):
            return financial_tools_node
        return "Analysis Gate"

    def _route_technical(self, state: AgentState) -> str:
        technical_tools_node = self._resolve_tool_node_name("technical")
        if technical_tools_node and self._has_tool_calls(state):
            return technical_tools_node
        return "Analysis Gate"

    def _route_news(self, state: AgentState) -> str:
        news_tools_node = self._resolve_tool_node_name("news")
        if news_tools_node and self._has_tool_calls(state):
            return news_tools_node
        return "Analysis Gate"

    def _analysis_gate_node(self, state: AgentState) -> Dict[str, Any]:
        return {}

    def _has_any_verification_reports(self, state: AgentState) -> bool:
        return bool(state.get("financial_verification_reports")) or bool(
            state.get("technical_verification_reports")
        ) or bool(state.get("news_verification_reports"))

    def _route_from_analysis_gate(self, state: AgentState) -> str:
        if self._has_any_verification_reports(state):
            return "Critic"
        return "Portfolio Manager"

    def _route_critic(self, state: AgentState) -> str:
        critic_tools_node = self._resolve_tool_node_name("critic")
        if critic_tools_node and self._has_tool_calls(state):
            return critic_tools_node
        return "Portfolio Manager"

    def _route_portfolio_manager(self, state: AgentState) -> str:
        portfolio_tools_node = self._resolve_tool_node_name("portfolio manager", "portfolio_manager")
        if portfolio_tools_node and self._has_tool_calls(state):
            return portfolio_tools_node
        return END

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
        workflow.add_node("Analysis Gate", self._analysis_gate_node)
        workflow.add_node("Critic", critic_node)
        workflow.add_node("Portfolio Manager", portfolio_manager_node)

        for agent_name, tool_node in self.tool_nodes.items():
            workflow.add_node(f"tools_{agent_name}", tool_node)

        workflow.add_edge(START, "Coordinator")

        coordinator_conditional_targets = ["Financial Analyst", "Technical Analyst", "News Analyst", "Analysis Gate"]
        coordinator_tools_node = self._resolve_tool_node_name("coordinator")
        if coordinator_tools_node:
            coordinator_conditional_targets.append(coordinator_tools_node)

        # Coordinator can repeatedly call tools, then fan-out with Send API
        workflow.add_conditional_edges(
            "Coordinator",
            self._route_from_coordinator,
            coordinator_conditional_targets,
        )
        if coordinator_tools_node:
            workflow.add_edge(coordinator_tools_node, "Coordinator")

        # Analysts can repeatedly call tools, then fan-in to analysis gate
        financial_conditional_targets = ["Analysis Gate"]
        financial_tools_node = self._resolve_tool_node_name("financial", "fundamental")
        if financial_tools_node:
            financial_conditional_targets.append(financial_tools_node)
        workflow.add_conditional_edges("Financial Analyst", self._route_financial, financial_conditional_targets)
        if financial_tools_node:
            workflow.add_edge(financial_tools_node, "Financial Analyst")

        technical_conditional_targets = ["Analysis Gate"]
        technical_tools_node = self._resolve_tool_node_name("technical")
        if technical_tools_node:
            technical_conditional_targets.append(technical_tools_node)
        workflow.add_conditional_edges("Technical Analyst", self._route_technical, technical_conditional_targets)
        if technical_tools_node:
            workflow.add_edge(technical_tools_node, "Technical Analyst")

        news_conditional_targets = ["Analysis Gate"]
        news_tools_node = self._resolve_tool_node_name("news")
        if news_tools_node:
            news_conditional_targets.append(news_tools_node)
        workflow.add_conditional_edges("News Analyst", self._route_news, news_conditional_targets)
        if news_tools_node:
            workflow.add_edge(news_tools_node, "News Analyst")

        workflow.add_conditional_edges(
            "Analysis Gate",
            self._route_from_analysis_gate,
            ["Critic", "Portfolio Manager"],
        )

        critic_conditional_targets = ["Portfolio Manager"]
        critic_tools_node = self._resolve_tool_node_name("critic")
        if critic_tools_node:
            critic_conditional_targets.append(critic_tools_node)
        workflow.add_conditional_edges("Critic", self._route_critic, critic_conditional_targets)
        if critic_tools_node:
            workflow.add_edge(critic_tools_node, "Critic")

        portfolio_conditional_targets = [END]
        portfolio_tools_node = self._resolve_tool_node_name("portfolio manager", "portfolio_manager")
        if portfolio_tools_node:
            portfolio_conditional_targets.append(portfolio_tools_node)
        workflow.add_conditional_edges("Portfolio Manager", self._route_portfolio_manager, portfolio_conditional_targets)
        if portfolio_tools_node:
            workflow.add_edge(portfolio_tools_node, "Portfolio Manager")

        return workflow.compile()
