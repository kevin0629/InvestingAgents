from typing import Optional

from .base_client import BaseEmbeddingClient
from .google_client import GoogleEmbeddingClient
from .openai_client import OpenAIEmbeddingClient


def create_embedding_client(
    provider: str,
    model: Optional[str] = None,
    **kwargs,
) -> BaseEmbeddingClient:
    """Create an embedding client for the specified provider.

    Args:
        provider: Embedding provider (openai, google)
        model: Embedding model name/identifier
        **kwargs: Additional provider-specific arguments

    Returns:
        Configured BaseEmbeddingClient instance

    Raises:
        ValueError: If provider is not supported
    """
    provider_lower = provider.lower()

    if provider_lower == "openai":
        selected_model = model or "text-embedding-3-small"
        return OpenAIEmbeddingClient(selected_model, **kwargs)

    if provider_lower == "google":
        selected_model = model or "gemini-embedding-001"
        return GoogleEmbeddingClient(selected_model, **kwargs)

    raise ValueError(f"Unsupported embedding provider: {provider}")
