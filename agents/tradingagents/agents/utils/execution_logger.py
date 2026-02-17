import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict


class AgentExecutionLogger:
    _lock = Lock()

    @staticmethod
    def _base_log_dir() -> Path:
        override = os.getenv("TRADINGAGENTS_AGENT_LOG_DIR")
        if override:
            return Path(override)
        return Path("logs") / "agent_runs"

    @staticmethod
    def _run_file(run_id: str) -> Path:
        run_dir = AgentExecutionLogger._base_log_dir() / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir / "events.jsonl"

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool, list, dict)):
            return value
        try:
            return str(value)
        except Exception:
            return "<unserializable>"

    @staticmethod
    def _truncate(value: Any, max_chars: int = 8000) -> Any:
        jsonable = AgentExecutionLogger._to_jsonable(value)
        if isinstance(jsonable, str) and len(jsonable) > max_chars:
            return jsonable[:max_chars] + "...<truncated>"
        return jsonable

    @staticmethod
    def log_event(run_id: str, event_type: str, node: str, payload: Dict[str, Any]):
        if not run_id:
            return
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "event_type": event_type,
            "node": node,
            "payload": AgentExecutionLogger._truncate(payload),
        }
        out_file = AgentExecutionLogger._run_file(run_id)
        with AgentExecutionLogger._lock:
            with out_file.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
