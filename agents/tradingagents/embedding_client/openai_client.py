from typing import List

from langchain_openai import OpenAIEmbeddings

from .base_client import BaseEmbeddingClient


class OpenAIEmbeddingClient(BaseEmbeddingClient):
    """Embedding client for OpenAI models via langchain-openai."""

    def get_embedding(self, text: str) -> List[float]:
        embedding_kwargs = {"model": self.model}

        for key in ("api_key", "openai_api_key", "base_url", "openai_api_base", "timeout", "max_retries"):
            if key in self.kwargs:
                embedding_kwargs[key] = self.kwargs[key]

        embeddings = OpenAIEmbeddings(**embedding_kwargs)
        return embeddings.embed_query(text)
