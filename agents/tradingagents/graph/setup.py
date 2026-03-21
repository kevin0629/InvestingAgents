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
    create_critic,
    create_financial_analyst,
    create_technical_analyst,
    create_news_analyst,
    create_portfolio_manager,
)
from tradingagents.agents.utils.agent_output_formats import (
    CoordinatorOutput,
    FinancialOutput,
    TechnicalOutput,
    NewsOutput,
    PortfolioDecisions,
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

    def _has_tool_calls(self, state: Dict[str, Any], message_key: str = "messages") -> bool:
        messages = state.get(message_key) or []
        if not messages:
            return False
        last_message = messages[-1]
        return bool(getattr(last_message, "tool_calls", None))

    def _resolve_tool_node_name(self, *keys: str) -> str | None:
        for key in keys:
            if key in self.tool_nodes:
                return f"tools_{key}"
        return None

    def _is_only_response_tool_call(self, state: Dict[str, Any], tool_name: str, message_key: str = "messages") -> bool:
        messages = state.get(message_key) or []
        if not messages:
            return False
        last_message = messages[-1]
        tool_calls = getattr(last_message, "tool_calls", None) or []
        return len(tool_calls) == 1 and tool_calls[0].get("name") == tool_name

    def _assign_analyst_workers(self, state: AgentState) -> List[Send]:
        sends: List[Send] = []

        def _task_has_symbol(task: Any) -> bool:
            if task is None:
                return False
            if isinstance(task, dict):
                return bool(task.get("symbol"))
            return bool(getattr(task, "symbol", None))

        # Pass every field the analyst nodes read directly via Send payload.
        # LangGraph's Send API gives the worker node ONLY what is in this dict —
        # it does NOT automatically inherit the parent graph's state.
        shared_ctx = {
            "user_query": state.get("user_query", ""),
            "mode": state.get("mode", ""),
            "market_situation": state.get("market_situation", ""),
            "end_date": state.get("end_date", ""),
            "strategy": state.get("strategy", ""),
        }

        if any(_task_has_symbol(task) for task in (state.get("financial_tasks") or [])):
            sends.append(Send("Financial Analyst", {
                **shared_ctx,
                "financial_tasks": state.get("financial_tasks", []),
                "financial_messages": state.get("financial_messages", []),
            }))

        if any(_task_has_symbol(task) for task in (state.get("technical_tasks") or [])):
            sends.append(Send("Technical Analyst", {
                **shared_ctx,
                "technical_tasks": state.get("technical_tasks", []),
                "technical_messages": state.get("technical_messages", []),
            }))

        if any(_task_has_symbol(task) for task in (state.get("news_tasks") or [])):
            sends.append(Send("News Analyst", {
                **shared_ctx,
                "news_tasks": state.get("news_tasks", []),
                "news_messages": state.get("news_messages", []),
            }))

        if not sends:
            sends.append(Send("Analysis Gate", {}))

        return sends

    def _route_from_coordinator(self, state: AgentState):
        if self._is_only_response_tool_call(state, CoordinatorOutput.__name__):
            return self._assign_analyst_workers(state)
        coordinator_tools_node = self._resolve_tool_node_name("coordinator")
        if coordinator_tools_node and self._has_tool_calls(state):
            return coordinator_tools_node
        return self._assign_analyst_workers(state)

    def _route_financial(self, state: AgentState) -> str:
        if self._is_only_response_tool_call(state, FinancialOutput.__name__, "financial_messages"):
            return "Analysis Gate"
        financial_tools_node = self._resolve_tool_node_name("financial", "fundamental")
        if financial_tools_node and self._has_tool_calls(state, "financial_messages"):
            return financial_tools_node
        return "Analysis Gate"

    def _route_technical(self, state: AgentState) -> str:
        if self._is_only_response_tool_call(state, TechnicalOutput.__name__, "technical_messages"):
            return "Analysis Gate"
        technical_tools_node = self._resolve_tool_node_name("technical")
        if technical_tools_node and self._has_tool_calls(state, "technical_messages"):
            return technical_tools_node
        return "Analysis Gate"

    def _route_news(self, state: AgentState) -> str:
        if self._is_only_response_tool_call(state, NewsOutput.__name__, "news_messages"):
            return "Analysis Gate"
        news_tools_node = self._resolve_tool_node_name("news")
        if news_tools_node and self._has_tool_calls(state, "news_messages"):
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
        if self._is_only_response_tool_call(state, PortfolioDecisions.__name__, "portfolio_messages"):
            return END
        portfolio_tools_node = self._resolve_tool_node_name("portfolio manager", "portfolio_manager")
        if portfolio_tools_node and self._has_tool_calls(state, "portfolio_messages"):
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
