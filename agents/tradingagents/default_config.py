import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai", # Options: openai, google
    "deep_think_llm": "gpt-5", # gpt-5
    "quick_think_llm": "gpt-5-mini", #gpt-5-mini
    "backend_url": "https://api.openai.com/v1",  # openai: https://api.openai.com/v1, https://generativelanguage.googleapis.com
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": "medium",    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Embedding settings for persistent reflection Agentic RAG
    "embedding_provider": "google",    # Options: openai, google
    "openai_embedding_model": "text-embedding-3-small",
    "google_embedding_model": "gemini-embedding-001",
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
