from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .base_client import BaseEmbeddingClient


class GoogleEmbeddingClient(BaseEmbeddingClient):
    """Embedding client for Google Gemini models via langchain-google-genai."""

    def get_embedding(self, text: str) -> List[float]:
        embedding_kwargs = {"model": self.model}

        for key in ("google_api_key", "api_key", "task_type"):
            if key in self.kwargs:
                embedding_kwargs[key] = self.kwargs[key]

        embeddings = GoogleGenerativeAIEmbeddings(**embedding_kwargs)
        return embeddings.embed_query(text)
