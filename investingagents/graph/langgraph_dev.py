from typing import Any, Dict
from default_config import DEFAULT_CONFIG
from .investing_graph import InvestingAgentsGraph


def build_graph(config: Dict[str, Any] | None = None):
    merged = DEFAULT_CONFIG.copy()
    if config:
        merged.update(config)
    graph = InvestingAgentsGraph(debug=True, config=merged)
    return graph.graph