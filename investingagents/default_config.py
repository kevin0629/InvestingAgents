import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    
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
    "embedding_dimension": 1536,    # Options: 384, 768, 1536, 3072, must lower than the max dimension of the embedding model
}
