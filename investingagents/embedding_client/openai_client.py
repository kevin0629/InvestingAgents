from typing import List
from langchain_openai import OpenAIEmbeddings
from .base_client import BaseEmbeddingClient
from .validators import validate_model


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """Embedding client for OpenAI models via langchain-openai."""
    def __init__(self, model: str, **kwargs):
        super().__init__(model, **kwargs)

    def get_embedding(self, text: str) -> List[float]:
        embedding_kwargs = {"model": self.model}

        for key in ("openai_api_key", "max_retries", "dimensions"):
            if key in self.kwargs:
                embedding_kwargs[key] = self.kwargs[key]

        embeddings = OpenAIEmbeddings(**embedding_kwargs)
        return embeddings.embed_query(text)

    def validate_model(self) -> bool:
        """Validate model for OpenAI."""
        return validate_model("openai", self.model)
