# TradingAgents/graph/conditional_logic.py

from tradingagents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""
    def should_continue_coordinator(self, state: AgentState):
        """Determine if coordinator should continue to next step."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_coordinator"
        return "Msg Clear Coordinator"

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

    def should_continue_financial(self, state: AgentState):
        """Determine if financial analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_financial"
        return "Msg Clear Financial"
    
    def should_continue_critic(self, state: AgentState):
        """Determine if critic should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_critic"
        return "Msg Clear Critic"
    
    def should_continue_portfolio_manager(self, state: AgentState):
        """Determine if portfolio manager should continue."""
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools_portfolio_manager"
        return "Msg Clear Portfolio Manager"
