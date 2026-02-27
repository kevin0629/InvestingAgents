from typing import Any, Dict

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.test_graph import TradingAgentsGraph


def build_graph(config: Dict[str, Any] | None = None):
    merged = DEFAULT_CONFIG.copy()
    if config:
        merged.update(config)
    graph = TradingAgentsGraph(debug=True, config=merged)
    return graph.graph