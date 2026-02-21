import json
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool

from tradingagents.dataflows.config import get_config
from tradingagents.dataflows.reflection_utils import retrieve_reflections, store_reflection
from tradingagents.dataflows.interface import route_to_vendor

_EMBEDDER = None
_EMBEDDER_KEY = None


def _resolved_config(extra_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    merged = get_config()
    if extra_config:
        merged.update(extra_config)
    return merged


def _provider(config: Dict[str, Any]) -> str:
    provider = str(config.get("embedding_provider", "openai")).strip().lower()
    if provider in {"google", "gemini"}:
        return "gemini"
    return "openai"


def _get_embedder(config: Dict[str, Any]):
    global _EMBEDDER, _EMBEDDER_KEY

    provider = _provider(config)
    if provider == "gemini":
        model_name = config.get("gemini_embedding_model", "gemini-embedding-001")
        key = (provider, model_name, None)
    else:
        model_name = config.get("openai_embedding_model", "text-embedding-3-small")
        backend_url = config.get("backend_url")
        key = (provider, model_name, backend_url)

    if _EMBEDDER is not None and _EMBEDDER_KEY == key:
        return _EMBEDDER

    if provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        _EMBEDDER = GoogleGenerativeAIEmbeddings(model=model_name, output_dimensionality=1536) # default dimensionality is 3072
    else:
        from langchain_openai import OpenAIEmbeddings

        if key[2]:
            _EMBEDDER = OpenAIEmbeddings(model=model_name, base_url=key[2])
        else:
            _EMBEDDER = OpenAIEmbeddings(model=model_name)

    _EMBEDDER_KEY = key
    return _EMBEDDER


def embed_text(text: str, config: Optional[Dict[str, Any]] = None) -> List[float]:
    resolved = _resolved_config(config)
    return _get_embedder(resolved).embed_query(text)


@tool
def retrieve_reflections(
    query: Annotated[str, "Query text for retrieving reflections"],
    strategy: Annotated[str, "Optional filter conditions, e.g. monthly_revenue_growth_roe"] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve reflection data for a given query.

    Args:
        query (str): Query text for retrieving reflections
        strategy (str): Optional filter conditions, e.g. monthly_revenue_growth_roe
    Returns:
        List[Dict[str, Any]]: A list of reflection data dictionaries
    """
    query_embedding = embed_text(query)
    filter_conditions = {"strategy": strategy} if strategy else None
    return route_to_vendor("retrieve_reflections", query_embedding, filter_conditions)


@tool
def store_reflection(
    reflection_text: Annotated[str, "Reflection text to store"],
    strategy: Annotated[str, "Optional filter conditions, e.g. monthly_revenue_growth_roe"] = None,
) -> str:
    """
    Store reflection data to Qdrant.
    
    Args:
        reflection_text: Reflection text to store
        strategy: Optional filter conditions, e.g. monthly_revenue_growth_roe
        
    Returns:
        str: "Stored in Qdrant with ID: " + reflection_id
        
    Raises:
        Exception: If both Qdrant and JSONL fallback fail
    """
    reflection_embedding = embed_text(reflection_text)
    metadata = {"strategy": strategy} if strategy else None
    return route_to_vendor("store_reflection", reflection_text, reflection_embedding, metadata)
