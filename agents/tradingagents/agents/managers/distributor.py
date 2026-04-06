"""Deterministic distributor subgraph (state-driven, non-LLM)."""

from __future__ import annotations

from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph

from tradingagents.agents.utils.agent_states import DistributorState
from tradingagents.dataflows.account_utils import get_stock_account
from tradingagents.dataflows.backtest_utils import (
    get_backtest_report,
    get_market_return,
    get_strategy,
)
from tradingagents.dataflows.fundamentals_utils import get_company_by_symbol


def _extract_return_value(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""

    performance = payload.get("performance")
    if isinstance(performance, dict):
        value = performance.get("return")
        if value is not None and str(value).strip() != "":
            return str(value)

    value = payload.get("return")
    if value is not None and str(value).strip() != "":
        return str(value)

    return ""


def _extract_symbols(backtest_report: Dict[str, Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    holdings = backtest_report.get("current_holdings") or []

    for row in holdings:
        symbol = str(row.get("stock_id") or row.get("stock") or "").strip()
        if symbol and symbol not in seen:
            seen.add(symbol)
            result.append(symbol)

    return result


def _extract_previous_holdings(account_payload: Dict[str, Any]) -> Dict[str, Any]:
    rows = account_payload.get("rows") or []
    prev_symbols: List[str] = []
    prev_buy_reason_map: Dict[str, str] = {}
    seen = set()

    for row in rows:
        symbol = str((row or {}).get("stock") or (row or {}).get("stock_id") or "").strip()
        if not symbol or symbol in seen:
            continue

        seen.add(symbol)
        prev_symbols.append(symbol)
        prev_buy_reason_map[symbol] = str((row or {}).get("buy_reason") or "").strip()

    return {
        "symbols": prev_symbols,
        "buy_reason_map": prev_buy_reason_map,
        "start_sig_date": str(account_payload.get("start_sig_date") or "").strip(),
        "performance_return": str(account_payload.get("performance_return") or "").strip(),
    }


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


def _task_type_for_symbol(symbol: str, previous_symbols: set[str]) -> str:
    if symbol in previous_symbols:
        return "HYBRID"

    return "ANALYSIS"


def _build_single_task_payload(
    symbol: str,
    task_type: str,
    selected: bool,
    buy_reason: str,
    company_info_map: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "task_type": task_type,
        "selected": selected,
        "buy_reason": buy_reason,
        "company_info": company_info_map.get(symbol, ""),
    }


def _build_tasks(
    symbols: List[str],
    company_info_map: Dict[str, str],
    previous_symbols: List[str],
    previous_buy_reason_map: Dict[str, str],
) -> Dict[str, List[Dict[str, Any]]]:
    current_symbol_set = set(symbols)
    previous_symbol_set = set(previous_symbols)
    financial_tasks: List[Dict[str, Any]] = []
    technical_tasks: List[Dict[str, Any]] = []
    news_tasks: List[Dict[str, Any]] = []

    for symbol in symbols:
        task_type = _task_type_for_symbol(symbol, previous_symbol_set)
        selected = task_type == "HYBRID"
        buy_reason = previous_buy_reason_map.get(symbol, "") if selected else ""

        task_payload = _build_single_task_payload(
            symbol=symbol,
            task_type=task_type,
            selected=selected,
            buy_reason=buy_reason,
            company_info_map=company_info_map,
        )
        financial_tasks.append(dict(task_payload))
        technical_tasks.append(dict(task_payload))
        news_tasks.append(dict(task_payload))

    # Previous-only symbols must be verified even when they are not selected this period.
    dropped_symbols = [symbol for symbol in previous_symbols if symbol not in current_symbol_set]
    for symbol in dropped_symbols:
        task_payload = _build_single_task_payload(
            symbol=symbol,
            task_type="VERIFICATION",
            selected=False,
            buy_reason=previous_buy_reason_map.get(symbol, ""),
            company_info_map=company_info_map,
        )
        financial_tasks.append(dict(task_payload))
        technical_tasks.append(dict(task_payload))
        news_tasks.append(dict(task_payload))

    return {
        "financial_tasks": financial_tasks,
        "technical_tasks": technical_tasks,
        "news_tasks": news_tasks,
    }


def create_distributor():
    """Return a compiled fixed-logic distributor subgraph."""

    def distributor_node(state: DistributorState):
        strategy_name = str(state.get("strategy") or "").strip()
        end_date = str(state.get("end_date") or "").strip()

        pre_market_performance = ""
        pre_strategy_performance = ""
        pre_performance = ""

        strategy_catalog = get_strategy()
        strategy_ok = _strategy_exists(strategy_name, strategy_catalog)

        previous_symbols: List[str] = []
        previous_buy_reason_map: Dict[str, str] = {}
        start_sig_date = ""

        if strategy_ok and end_date:
            previous_account = get_stock_account(strategy=strategy_name, end_date=end_date)
            previous_info = _extract_previous_holdings(previous_account)
            previous_symbols = previous_info["symbols"]
            previous_buy_reason_map = previous_info["buy_reason_map"]
            start_sig_date = previous_info["start_sig_date"]
            pre_performance = previous_info["performance_return"]

        backtest_report: Dict[str, Any] = {}
        market_return_report: Dict[str, Any] = {}

        if strategy_ok:
            if start_sig_date:
                backtest_report = get_backtest_report(
                    strategy_name=strategy_name,
                    start_date=start_sig_date,
                    end_date=end_date,
                )
                market_return_report = get_market_return(
                    start_date=start_sig_date,
                    end_date=end_date,
                )
            else:
                backtest_report = get_backtest_report(strategy_name=strategy_name, end_date=end_date)

        if market_return_report:
            pre_market_performance = _extract_return_value(market_return_report)

        if backtest_report and start_sig_date:
            pre_strategy_performance = _extract_return_value(backtest_report)

        symbols = _extract_symbols(backtest_report)

        all_task_symbols = list(dict.fromkeys(symbols + previous_symbols))

        company_profiles: Dict[str, str] = {}
        for symbol in all_task_symbols:
            company_profiles[symbol] = get_company_by_symbol(symbol)

        tasks = _build_tasks(
            symbols=symbols,
            company_info_map=company_profiles,
            previous_symbols=previous_symbols,
            previous_buy_reason_map=previous_buy_reason_map,
        )

        strategy_description = _strategy_description(strategy_name, strategy_catalog)

        return {
            "end_date": end_date,
            "strategy": strategy_name if strategy_ok else "",
            "financial_tasks": tasks["financial_tasks"],
            "technical_tasks": tasks["technical_tasks"],
            "news_tasks": tasks["news_tasks"],
            "pre_market_performance": pre_market_performance,
            "pre_strategy_performance": pre_strategy_performance,
            "pre_performance": pre_performance,
            # Additional context for downstream agents / logging
            "strategy_description": strategy_description,
            "company_info_map": company_profiles,
            "backtest_report": backtest_report,
            "market_return_report": market_return_report,
        }

    sg = StateGraph(DistributorState)
    sg.add_node("distributor", distributor_node)
    sg.add_edge(START, "distributor")
    sg.add_edge("distributor", END)
    return sg.compile()
