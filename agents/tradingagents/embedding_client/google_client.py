from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .base_client import BaseEmbeddingClient
from .validators import validate_model


class GoogleEmbeddingClient(BaseEmbeddingClient):
    """Embedding client for Google Gemini models via langchain-google-genai."""
    def __init__(self, model: str, **kwargs):
        super().__init__(model, **kwargs)

    def get_embedding(self, text: str) -> List[float]:
        embedding_kwargs = {"model": self.model}

        for key in ("output_dimensionality"):
            if key in self.kwargs:
                embedding_kwargs[key] = self.kwargs[key]

        embeddings = GoogleGenerativeAIEmbeddings(**embedding_kwargs)
        return embeddings.embed_query(text)
    
    def validate_model(self) -> bool:
        """Validate model for Google."""
        return validate_model("google", self.model)
