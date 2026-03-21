import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from tradingagents.agents.utils.execution_logger import AgentExecutionLogger
from tradingagents.agents.utils.langfuse_tracing import create_langfuse_callback
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.propagation import Propagator
from tradingagents.graph.setup_test import GraphSetup
from tradingagents.llm_clients import create_llm_client



class TradingAgentsGraph:
    """
    trading workflow:
    Distributor -> Macro, Financial, Technical, News -> Critic -> Portfolio Manager.
    """

    def __init__(
        self,
        debug: bool = False,
        config: Optional[Dict[str, Any]] = None,
        callbacks: Optional[List] = None,
    ):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = list(callbacks or [])

        # langfuse_callback = create_langfuse_callback(
        #     trace_name="InvestingAgentsGraph",
        #     session_id=self.config.get("langfuse_session_id"),
        # )
        # if langfuse_callback is not None:
        #     self.callbacks.append(langfuse_callback)

        set_config(self.config)

        # os.makedirs(
        #     os.path.join(self.config["project_dir"], "dataflows/data_cache"),
        #     exist_ok=True,
        # )

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

        self.graph_setup = GraphSetup(
            quick_thinking_llm=self.quick_thinking_llm,
            deep_thinking_llm=self.deep_thinking_llm,
        )
        self.propagator = Propagator(max_recur_limit=self.config.get("max_recur_limit", 100))

        self.graph = self.graph_setup.setup_graph()
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

    def propagate(self, user_request: str):
        """Run the workflow and return final state + normalized decision."""
        run_id = datetime.now().isoformat()
        init_agent_state = self.propagator.create_initial_state(user_request=user_request)
        AgentExecutionLogger.log_event(
            run_id,
            "graph_start",
            "TradingAgentsGraph",
            {"user_request": user_request},
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
        self._log_state(final_state)
        return final_state, self.process_signal(final_state.get("final_trade_decision", ""))

    def _log_state(self, final_state: Dict[str, Any]):
        end_date = final_state.get("end_date")
        self.log_states_dict[str(end_date)] = {
            "run_id": final_state.get("run_id"),
            "company_of_interest": final_state.get("company_of_interest"),
            "end_date": end_date,
            "mode": final_state.get("mode"),
            "strategy": final_state.get("strategy"),
            "strategy_description": final_state.get("strategy_description"),
            "backtest_report": final_state.get("backtest_report"),
            "company_info_map": final_state.get("company_info_map"),
            "market_regime": final_state.get("market_regime"),
            "coordinator_plan": final_state.get("coordinator_plan"),
            "financial_reports": final_state.get("financial_reports"),
            "technical_reports": final_state.get("technical_reports"),
            "news_reports": final_state.get("news_reports"),
            "macro_analysis_report": final_state.get("macro_analysis_report"),
            "critic_reflections": final_state.get("critic_reflections"),
            "portfolio_decision": final_state.get("portfolio_decision"),
            "final_trade_decision": final_state.get("final_trade_decision"),
        }

        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)
        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{end_date}.json",
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(self.log_states_dict, file, indent=2, ensure_ascii=False)
