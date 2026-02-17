import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.execution_logger import AgentExecutionLogger
from tradingagents.agents.utils.langfuse_tracing import create_langfuse_callback
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.setup import GraphSetup
from tradingagents.llm_clients import create_llm_client


class TradingAgentsGraph:
    """README-aligned trading workflow:
    Coordinator -> Financial -> Technical -> News -> Critic -> Portfolio Manager.
    """

    def __init__(
        self,
        selected_analysts=None,
        debug: bool = False,
        config: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None,
    ):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = list(callbacks or [])

        langfuse_callback = create_langfuse_callback(
            trace_name="InvestingAgentsGraph",
            session_id=self.config.get("langfuse_session_id"),
        )
        if langfuse_callback is not None:
            self.callbacks.append(langfuse_callback)

        set_config(self.config)

        llm_kwargs = self._get_provider_kwargs()
        if self.callbacks:
            llm_kwargs["callbacks"] = self.callbacks

        deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )
        quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **llm_kwargs,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()

        self.reflection_memory = FinancialSituationMemory("critic_reflection_memory", self.config)

        self.graph_setup = GraphSetup(
            quick_thinking_llm=self.quick_thinking_llm,
            deep_thinking_llm=self.deep_thinking_llm,
            reflection_memory=self.reflection_memory,
        )
        self.propagator = Propagator(max_recur_limit=self.config.get("max_recur_limit", 100))

        self.graph = self.graph_setup.setup_graph(selected_analysts)
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}

    def _get_provider_kwargs(self) -> Dict[str, Any]:
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()
        if provider == "google":
            thinking_level = self.config.get("google_thinking_level")
            if thinking_level:
                kwargs["thinking_level"] = thinking_level
        elif provider == "openai":
            reasoning_effort = self.config.get("openai_reasoning_effort")
            if reasoning_effort:
                kwargs["reasoning_effort"] = reasoning_effort
        return kwargs

    def propagate(self, company_name: str, trade_date: str, user_request: Optional[str] = None):
        """Run the workflow and return final state + normalized decision."""
        self.ticker = company_name
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        init_agent_state = self.propagator.create_initial_state(
            company_name=company_name,
            trade_date=trade_date,
            user_request=user_request or company_name,
            run_id=run_id,
        )
        AgentExecutionLogger.log_event(
            run_id,
            "graph_start",
            "TradingAgentsGraph",
            {"company": company_name, "trade_date": trade_date, "user_request": user_request or company_name},
        )
        args = self.propagator.get_graph_args(callbacks=self.callbacks if self.callbacks else None)

        if self.debug:
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                trace.append(chunk)
                messages = chunk.get("messages", [])
                if messages:
                    last = messages[-1]
                    tool_calls = getattr(last, "tool_calls", None)
                    AgentExecutionLogger.log_event(
                        run_id,
                        "graph_chunk",
                        "TradingAgentsGraph",
                        {
                            "message_type": last.__class__.__name__,
                            "content": getattr(last, "content", None),
                            "tool_calls": tool_calls,
                        },
                    )
            final_state = trace[-1] if trace else self.graph.invoke(init_agent_state, **args)
        else:
            final_state = self.graph.invoke(init_agent_state, **args)

        self.curr_state = final_state
        AgentExecutionLogger.log_event(
            run_id,
            "graph_end",
            "TradingAgentsGraph",
            {
                "final_trade_decision": final_state.get("final_trade_decision"),
                "portfolio_decision": final_state.get("portfolio_decision"),
            },
        )
        self._log_state(trade_date, final_state)
        return final_state, self.process_signal(final_state.get("final_trade_decision", ""))

    def _log_state(self, trade_date: str, final_state: Dict[str, Any]):
        self.log_states_dict[str(trade_date)] = {
            "run_id": final_state.get("run_id"),
            "company_of_interest": final_state.get("company_of_interest"),
            "trade_date": final_state.get("trade_date"),
            "mode": final_state.get("mode"),
            "market_regime": final_state.get("market_regime"),
            "coordinator_plan": final_state.get("coordinator_plan"),
            "financial_reports": final_state.get("financial_reports"),
            "technical_reports": final_state.get("technical_reports"),
            "news_reports": final_state.get("news_reports"),
            "critic_reflections": final_state.get("critic_reflections"),
            "portfolio_decision": final_state.get("portfolio_decision"),
            "final_trade_decision": final_state.get("final_trade_decision"),
        }

        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)
        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(self.log_states_dict, file, indent=2, ensure_ascii=False)

    def reflect_and_remember(self, returns_losses):
        """Append lightweight post-trade reflection into memory for future critic retrieval."""
        if not self.curr_state:
            return
        summary = {
            "returns_losses": returns_losses,
            "final_trade_decision": self.curr_state.get("final_trade_decision"),
            "market_regime": self.curr_state.get("market_regime"),
        }
        situation = json.dumps(
            {
                "financial_reports": self.curr_state.get("financial_reports", []),
                "technical_reports": self.curr_state.get("technical_reports", []),
                "news_reports": self.curr_state.get("news_reports", []),
            },
            ensure_ascii=False,
        )
        self.reflection_memory.add_situations(
            [(situation, json.dumps(summary, ensure_ascii=False))]
        )

    def process_signal(self, full_signal: str) -> str:
        """Extract BUY/SELL/HOLD from portfolio JSON output."""
        if not full_signal:
            return "HOLD"
        try:
            payload = json.loads(full_signal)
            if "final_action" in payload:
                action = str(payload["final_action"]).upper()
                if "BUY" in action:
                    return "BUY"
                if "SELL" in action:
                    return "SELL"
                return "HOLD"
            decisions = payload.get("portfolio_decisions", [])
            if decisions:
                first = str(decisions[0].get("action", "HOLD")).upper()
                if "OPEN" in first or "ADD" in first or "BUY" in first:
                    return "BUY"
                if "CLOSE" in first or "REDUCE" in first or "SELL" in first:
                    return "SELL"
        except Exception:
            signal = full_signal.upper()
            if "BUY" in signal:
                return "BUY"
            if "SELL" in signal:
                return "SELL"
        return "HOLD"
