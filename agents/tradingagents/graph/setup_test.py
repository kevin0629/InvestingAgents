"""
Graph assembly (test version).

setup_graph(llm) ??compiled StateGraph

Architecture:
  coordinator ?�?�(Send API)?�?�??financial_agent ?�??
                          ?�?�??technical_agent ?�?�?��???analysts_done ?�?�(has verification?)?�?�??critic ?�?�??portfolio_manager
                          ?�?�??news_agent      ?�??                 ?�?�(no verification?)?�?�?�?�?�?�?�?�?�?�?�?�?�?�??portfolio_manager
"""

from typing import Literal

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.managers.coordinator_test import create_coordinator
from tradingagents.agents.analysts.financial_analyst_test import create_financial_analyst
from tradingagents.agents.analysts.technical_analyst_test import create_technical_analyst
from tradingagents.agents.analysts.news_analyst_test import create_news_analyst
from tradingagents.agents.critic.critic_test import create_critic
from tradingagents.agents.trader.portfolio_manager_test import create_portfolio_manager



# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------
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

    def _route_tasks(self, state: AgentState):
        """Coordinator 完�?後、�? analyst ??Send API ??parallel 派送�?
        end_date ??Send payload ?��?示�??�含?��?（Send API ?�親 state ?�自?��??��??��?）�?
        """
        end_date = state.get("end_date", "")
        sends = []
        for task in state.get("financial_tasks", []):
            sends.append(Send("financial_agent", {"task": task, "end_date": end_date}))
        for task in state.get("technical_tasks", []):
            sends.append(Send("technical_agent", {"task": task, "end_date": end_date}))
        for task in state.get("news_tasks", []):
            sends.append(Send("news_agent", {"task": task, "end_date": end_date}))
        # ?�ス?��??��??��???fan-in ?�直??
        if not sends:
            sends.append(Send("analysts_done", {}))
        return sends


    def _route_after_analysts(self, state: AgentState) -> Literal["critic", "portfolio_manager"]:
        """VerificationReport ?��??�ば Critic ?�、な?��??�直??Portfolio Manager ?��?"""
        has_verification = (
            bool(state.get("financial_verification_reports"))
            or bool(state.get("technical_verification_reports"))
            or bool(state.get("news_verification_reports"))
        )
        return "critic" if has_verification else "portfolio_manager"


    # ---------------------------------------------------------------------------
    # Graph factory
    # ---------------------------------------------------------------------------

    def setup_graph(self):
        """Build and compile the full agent graph."""
        coordinator_node      = create_coordinator(self.deep_thinking_llm)
        financial_agent       = create_financial_analyst(self.quick_thinking_llm)
        technical_agent       = create_technical_analyst(self.quick_thinking_llm)
        news_agent            = create_news_analyst(self.quick_thinking_llm)
        critic_node           = create_critic(self.deep_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(self.deep_thinking_llm)

        workflow = StateGraph(AgentState)

        # ?�?� Nodes ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
        workflow.add_node("coordinator",       coordinator_node)
        workflow.add_node("financial_agent",   financial_agent)
        workflow.add_node("technical_agent",   technical_agent)
        workflow.add_node("news_agent",        news_agent)
        workflow.add_node("analysts_done",     lambda state: {})   # fan-in point
        workflow.add_node("critic",            critic_node)
        workflow.add_node("portfolio_manager", portfolio_manager_node)

        # ?�?� Edges ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
        workflow.add_edge(START, "coordinator")

        # Coordinator ??analysts (Send API, parallel fan-out)
        workflow.add_conditional_edges(
            "coordinator",
            self._route_tasks,
            ["financial_agent", "technical_agent", "news_agent", "analysts_done"],
        )

        # All analysts ??fan-in
        workflow.add_edge("financial_agent", "analysts_done")
        workflow.add_edge("technical_agent", "analysts_done")
        workflow.add_edge("news_agent",      "analysts_done")

        # Fan-in ??critic or portfolio_manager
        workflow.add_conditional_edges(
            "analysts_done",
            self._route_after_analysts,
            ["critic", "portfolio_manager"],
        )

        workflow.add_edge("critic", "portfolio_manager")
        workflow.add_edge("portfolio_manager", END)

        return workflow.compile()
