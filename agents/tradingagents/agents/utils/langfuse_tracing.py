import os
from typing import Optional


def create_langfuse_callback(trace_name: str, session_id: Optional[str] = None):
    enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return None

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if not public_key or not secret_key:
        return None

    try:
        from langfuse.callback import CallbackHandler
    except Exception:
        return None

    try:
        callback = CallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            trace_name=trace_name,
            session_id=session_id,
            tags=["investingagents", "local-debug"],
        )
    except Exception:
        return None

    return callback
