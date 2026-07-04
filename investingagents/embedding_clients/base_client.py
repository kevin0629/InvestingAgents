from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingClient(ABC):
    """Abstract base class for embedding clients."""

    def __init__(self, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs
    
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Return embedding vector for a single text input."""
        pass

    @abstractmethod
    def validate_model(self) -> bool:
        """Validate that the model is supported by this client."""
        pass
