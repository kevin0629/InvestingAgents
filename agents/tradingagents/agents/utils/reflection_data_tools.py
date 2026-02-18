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


def _collection_name(config: Dict[str, Any]) -> str:
    return str(config.get("reflection_collection_name", "critic_reflections"))


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

        _EMBEDDER = GoogleGenerativeAIEmbeddings(model=model_name)
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
    return _get_embedder(resolved).embed_text(text)


def store_reflection_text(
    reflection_text: str,
    metadata: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    resolved = _resolved_config(config)
    payload = dict(metadata or {})
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    payload.setdefault("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    vector = embed_text(reflection_text, resolved)
    return store_reflection(
        reflection_text=reflection_text,
        embedding=vector,
        metadata=payload,
        collection_name=_collection_name(resolved),
        fallback_to_jsonl=True,
    )


def retrieve_by_query(
    query_text: str,
    limit: Optional[int] = None,
    score_threshold: Optional[float] = None,
    filter_conditions: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    resolved = _resolved_config(config)
    top_k = int(limit or resolved.get("reflection_top_k", 5))
    vector = embed_text(query_text, resolved)
    try:
        return retrieve_reflections(
            query_embedding=vector,
            limit=top_k,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions,
            collection_name=_collection_name(resolved),
        )
    except Exception:
        return []


def add_situations(situations_and_advice: List[Tuple[str, str]], config: Optional[Dict[str, Any]] = None):
    for situation, recommendation in situations_and_advice:
        text = recommendation if recommendation else situation
        metadata = {
            "situation": situation,
            "recommendation": recommendation,
            "source": "critic",
        }
        store_reflection_text(text, metadata=metadata, config=config)


def get_memories(
    current_situation: str,
    n_matches: int = 1,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    hits = retrieve_by_query(current_situation, limit=n_matches, config=config)
    memories: List[Dict[str, Any]] = []
    for hit in hits:
        metadata = hit.get("metadata") or {}
        memories.append(
            {
                "matched_situation": metadata.get("situation", ""),
                "recommendation": hit.get("reflection_text", ""),
                "similarity_score": hit.get("score", 0.0),
            }
        )
    return memories


def clear():
    return None


@tool
def retrieve_reflections(
    query: Annotated[str, "Query text for retrieving reflections"],
    strategy: Annotated[str, "Optional filter conditions, e.g. revenue_growth_roe"] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve reflection data for a given query.

    Args:
        query (str): Query text for retrieving reflections
        strategy (str): Optional filter conditions, e.g. revenue_growth_roe
    Returns:
        List[Dict[str, Any]]: A list of reflection data dictionaries
    """
    query_embedding = embed_text(query)
    filter_conditions = {"strategy": strategy} if strategy else None
    return route_to_vendor("retrieve_reflections", query_embedding, filter_conditions)


@tool
def store_reflection(
    reflection_text: Annotated[str, "Reflection text to store"],
    strategy: Annotated[str, "Optional filter conditions, e.g. revenue_growth_roe"] = None,
) -> str:
    """
    Store reflection data to Qdrant.
    
    Args:
        reflection_text: Reflection text to store
        strategy: Optional filter conditions, e.g. revenue_growth_roe
        
    Returns:
        str: "Stored in Qdrant with ID: " + reflection_id
        
    Raises:
        Exception: If both Qdrant and JSONL fallback fail
    """
    reflection_embedding = embed_text(reflection_text)
    metadata = {"strategy": strategy} if strategy else None
    return route_to_vendor("store_reflection", reflection_text, reflection_embedding, metadata)
