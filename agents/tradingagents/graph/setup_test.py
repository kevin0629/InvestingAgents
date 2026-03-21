"""
Graph assembly (test version).

setup_graph(llm) ??compiled StateGraph

Architecture:
    distributor ?�?�(Send API)?�?�??macro_agent ?�??
                                                    ?�?�??financial_agent ?�??
                                                    ?�?�??technical_agent ?�?�?��???analysts_done ?�?�(has verification?)?�?�??critic ?�?�??portfolio_manager
                                                    ?�?�??news_agent      ?�??                 ?�?�(no verification?)?�?�?�?�?�?�?�?�?�?�?�?�?�?�??portfolio_manager
"""

from typing import Literal

from langchain_openai import ChatOpenAI
from langgraph.constants import Send
from langgraph.graph import END, START, StateGraph
from langfuse.langchain import CallbackHandler

from tradingagents.agents import (
    AgentState,
    create_distributor,
    create_financial_analyst,
    create_technical_analyst,
    create_news_analyst,
    create_macro_analyst,
    create_critic,
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

    def _route_tasks(self, state: AgentState):
        end_date = state.get("end_date", "")
        sends = []
        sends.append(Send("macro_agent", {"end_date": end_date}))
        for task in state.get("financial_tasks", []):
            sends.append(Send("financial_agent", {"task": task, "end_date": end_date}))
        for task in state.get("technical_tasks", []):
            sends.append(Send("technical_agent", {"task": task, "end_date": end_date}))
        for task in state.get("news_tasks", []):
            sends.append(Send("news_agent", {"task": task, "end_date": end_date}))
        return sends


    def _route_after_analysts(self, state: AgentState) -> Literal["critic", "portfolio_manager"]:
        has_verification = (
            bool(state.get("financial_verification_reports"))
            or bool(state.get("technical_verification_reports"))
            or bool(state.get("news_verification_reports"))
        )
        return "critic" if has_verification else "portfolio_manager"
    

    def setup_graph(self):
        """Build and compile the full agent graph."""
        langfuse_handler = CallbackHandler()
        
        distributor_node      = create_distributor()
        financial_agent       = create_financial_analyst(self.quick_thinking_llm)
        technical_agent       = create_technical_analyst(self.quick_thinking_llm)
        news_agent            = create_news_analyst(self.quick_thinking_llm)
        macro_agent           = create_macro_analyst(self.quick_thinking_llm)
        critic_node           = create_critic(self.deep_thinking_llm)
        portfolio_manager_node = create_portfolio_manager(self.deep_thinking_llm)

        workflow = StateGraph(AgentState)

        workflow.add_node("distributor",       distributor_node)
        workflow.add_node("macro_agent",       macro_agent)
        workflow.add_node("financial_agent",   financial_agent)
        workflow.add_node("technical_agent",   technical_agent)
        workflow.add_node("news_agent",        news_agent)
        workflow.add_node("analysts_done",     lambda state: {})   # fan-in point
        workflow.add_node("critic",            critic_node)
        workflow.add_node("portfolio_manager", portfolio_manager_node)

        workflow.add_edge(START, "distributor")

        workflow.add_conditional_edges(
            "distributor",
            self._route_tasks,
            ["macro_agent", "financial_agent", "technical_agent", "news_agent", "analysts_done"],
        )

        workflow.add_edge("macro_agent", "analysts_done")
        workflow.add_edge("financial_agent", "analysts_done")
        workflow.add_edge("technical_agent", "analysts_done")
        workflow.add_edge("news_agent",      "analysts_done")

        workflow.add_conditional_edges(
            "analysts_done",
            self._route_after_analysts,
            ["critic", "portfolio_manager"],
        )

        workflow.add_edge("critic", "portfolio_manager")
        workflow.add_edge("portfolio_manager", END)

        return workflow.compile().with_config({"callbacks": [langfuse_handler]})
