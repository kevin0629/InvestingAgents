"""Deterministic distributor subgraph (state-driven, non-LLM)."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph

from tradingagents.agents.utils.agent_states import CoordinatorState
from tradingagents.agents.utils.agent_utils import (
    get_backtest_report,
    get_company_info,
    get_strategy,
)


# def _invoke_tool(tool: Any, payload: Dict[str, Any] | None = None) -> Any:
# 	payload = payload or {}
# 	if hasattr(tool, "invoke"):
# 		return tool.invoke(payload)
# 	return tool(**payload)


# def _to_dict(value: Any) -> Dict[str, Any]:
# 	if isinstance(value, dict):
# 		return value
# 	if isinstance(value, str):
# 		try:
# 			parsed = json.loads(value)
# 			if isinstance(parsed, dict):
# 				return parsed
# 		except Exception:
# 			return {}
# 	return {}


# def _to_text(value: Any) -> str:
# 	if value is None:
# 		return ""
# 	if isinstance(value, str):
# 		return value
# 	return str(value)


def _extract_symbols(backtest_report: Dict[str, Any]) -> List[str]:
	result: List[str] = []
	holdings = backtest_report.get("current_holdings") or []
	for row in holdings:
		symbol = str(row.get("stock_id") or "").strip()
		result.append(symbol)
	return result


def _strategy_exists(strategy_name: str, strategy_catalog: Dict[str, Any]) -> bool:
	if not strategy_name:
		return False

	for row in strategy_catalog.get("strategies") or []:
		name = str(row.get("name") or "").strip()
		if name.lower() == strategy_name.lower():
			return True
	return False


def _strategy_description(strategy_name: str, strategy_catalog: Dict[str, Any]) -> str:
	for row in strategy_catalog.get("strategies") or []:
		name = str(row.get("name") or "").strip()
		if name.lower() == strategy_name.lower():
			return str(row.get("description") or "")
	return ""


def _build_tasks(symbols: List[str], company_info_map: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
	task_type = "ANALYSIS"
	financial_tasks: List[Dict[str, Any]] = []
	technical_tasks: List[Dict[str, Any]] = []
	news_tasks: List[Dict[str, Any]] = []

	for symbol in symbols:
		financial_tasks.append(
			{
				"symbol": symbol,
				"task_type": task_type,
				"buy_reason": None,
				"company_info": company_info_map.get(symbol, ""),
			}
		)
		technical_tasks.append(
			{
				"symbol": symbol,
				"task_type": task_type,
				"buy_reason": None,
				"company_info": company_info_map.get(symbol, ""),
			}
		)
		news_tasks.append(
			{
				"symbol": symbol,
				"task_type": task_type,
				"buy_reason": None,
				"company_info": company_info_map.get(symbol, ""),
			}
		)

	return {
		"financial_tasks": financial_tasks,
		"technical_tasks": technical_tasks,
		"news_tasks": news_tasks,
	}


def create_distributor():
	"""Return a compiled fixed-logic distributor subgraph."""

	def distributor_node(state: CoordinatorState):
		strategy_name = str(state.get("strategy") or "").strip()
		end_date = str(state.get("end_date") or "").strip()

		strategy_catalog = get_strategy()
		strategy_ok = _strategy_exists(strategy_name, strategy_catalog)

		backtest_report: Dict[str, Any] = {}
		if strategy_ok:
			backtest_report = get_backtest_report(strategy_name, end_date)

		symbols = _extract_symbols(backtest_report)

		company_profiles = {}
		for symbol in symbols:
			company_profiles[symbol] = get_company_info(symbol)

		tasks = _build_tasks(symbols, company_profiles)

		strategy_description = _strategy_description(strategy_name, strategy_catalog)
		backtest_summary = backtest_report.get("message", "") if isinstance(backtest_report, dict) else ""

		return {
			"end_date": end_date,
			"strategy": strategy_name if strategy_ok else "",
			"financial_tasks": tasks["financial_tasks"],
			"technical_tasks": tasks["technical_tasks"],
			"news_tasks": tasks["news_tasks"],
			# Additional context for downstream agents / logging
			"strategy_description": strategy_description,
			"backtest_report": backtest_summary,
			"company_info_map": company_profiles,
		}

	sg = StateGraph(CoordinatorState)
	sg.add_node("distributor", distributor_node)
	sg.add_edge(START, "distributor")
	sg.add_edge("distributor", END)
	return sg.compile()