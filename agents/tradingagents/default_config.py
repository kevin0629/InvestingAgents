import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Embedding settings for persistent reflection Agentic RAG
    "embedding_provider": "openai",    # Options: openai, gemini
    "openai_embedding_model": "text-embedding-3-small",
    "gemini_embedding_model": "gemini-embedding-001",
    "reflection_collection_name": "critic_reflections",
    "reflection_top_k": int(os.getenv("REFLECTION_TOP_K", "5")),
    # Local observability/tracing
    "langfuse_session_id": None,
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "stock_data": "myself",       # Options: alpha_vantage, yfinance
        "fundamental_data": "myself",      # Options: alpha_vantage, yfinance
        "news_data": "myself",             # Options: alpha_vantage, yfinance
        "backtest_data": "myself",          # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}
