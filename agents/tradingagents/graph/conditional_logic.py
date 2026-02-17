# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def should_continue_technical(self, state: AgentState):
        """Determine if technical analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_technical"
        return "Msg Clear Technical"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamental(self, state: AgentState):
        """Determine if fundamental analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_fundamental"
        return "Msg Clear Fundamental"
