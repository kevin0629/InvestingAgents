"""Model name validators for each provider.

Only validates model names - does NOT enforce limits.
Let Embedding providers use their own defaults for unspecified params.
"""

VALID_MODELS = {
    "openai": [
        # default length of embedding vector is 1536 dimensions
        "text-embedding-3-small",
        # default length of embedding vector is 3072 dimensions
        "text-embedding-3-large",
    ],
    "google": [
        # Gemini multimodal embedding model (preview), default length of embedding vector is 3072 dimensions
        "gemini-embedding-2-preview",
        # Gemini text embedding model, default length of embedding vector is 3072 dimensions
        "gemini-embedding-001",
    ],
}


def validate_model(provider: str, model: str) -> bool:
    """Check if model name is valid for the given provider.

    For ollama, openrouter - any model is accepted.
    """
    provider_lower = provider.lower()

    if provider_lower in ("ollama", "openrouter"):
        return True

    if provider_lower not in VALID_MODELS:
        return True

    return model in VALID_MODELS[provider_lower]
