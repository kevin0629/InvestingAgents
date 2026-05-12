import os
import json
import uuid
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    DatetimeRange,
)
from pathlib import Path
from functools import lru_cache
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.embedding_client import create_embedding_client


def get_embedding(text: str) -> List[float]:
    """Compute embedding for `text` using provider specified in `DEFAULT_CONFIG`.

    Notes:
    - The function selects an embedding client by `DEFAULT_CONFIG['embedding_provider']`.
    - For OpenAI it requests a 1536-dimension embedding (`text-embedding-3-small`).
    - For Google/Gemini it requests a 1536-dimension embedding (`gemini-embedding-001`).
    - Returns a list of floats representing the vector embedding.
    """
    kwargs = {}
    provider = DEFAULT_CONFIG.get("embedding_provider", "openai")
    if provider == "openai":
        model = DEFAULT_CONFIG.get("openai_embedding_model", "text-embedding-3-small")
        kwargs = {"dimensions": 1536}
    elif provider in ("google"):
        model = DEFAULT_CONFIG.get("gemini_embedding_model", "gemini-embedding-001")
        kwargs = {"output_dimensionality": 1536}
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")

    embedding_client = create_embedding_client(provider=provider, model=model, **kwargs)
    return embedding_client.get_embedding(text)



@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Return a cached QdrantClient instance.

    The client is created from the `QDRANT_URL` and optional `QDRANT_API_KEY`
    environment variables. The result is cached (LRU) so repeated calls reuse
    the same client object.
    """
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)
    
    return client


def store_reflections(
    reflection_text: Union[str, List[Union[str, Dict[str, Any]]], Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Store reflection data (single or batch) into Qdrant/JSONL fallback.

    Supported input forms:
    - Single mode: reflection_text is str, metadata is optional dict.
        - Batch mode: reflection_text is List[str] or List[Dict].
            For List[str], shared metadata will be applied to each item.
            For List[Dict], each item supports {"reflection_text": str, "metadata": Dict[str, Any]}.
    - Dict mode: reflection_text is Dict with keys above.
    """
    if isinstance(reflection_text, list):
        if not reflection_text:
            return "No reflections to store"

        results: List[str] = []
        success_count = 0
        for index, row in enumerate(reflection_text):
            row_text = ""
            row_metadata = dict(metadata or {})
            if isinstance(row, str):
                row_text = row.strip()
            elif isinstance(row, dict):
                row_text = str(row.get("reflection_text") or "").strip()
                per_row_metadata = row.get("metadata")
                if per_row_metadata is not None and not isinstance(per_row_metadata, dict):
                    results.append(f"[{index}] skipped: metadata must be dict")
                    continue
                if isinstance(per_row_metadata, dict):
                    row_metadata.update(per_row_metadata)
            else:
                results.append(f"[{index}] skipped: item must be str or dict")
                continue

            if not row_text:
                results.append(f"[{index}] skipped: reflection_text is empty")
                continue

            result = _store_single_reflection(row_text, row_metadata)
            results.append(f"[{index}] {result}")
            if result.startswith("Stored in"):
                success_count += 1

        return f"Batch store completed: {success_count}/{len(reflection_text)} succeeded\n" + "\n".join(results)

    if isinstance(reflection_text, dict):
        row_text = str(reflection_text.get("reflection_text") or "").strip()
        row_metadata = reflection_text.get("metadata")
        if row_metadata is not None and not isinstance(row_metadata, dict):
            row_metadata = None
        return _store_single_reflection(row_text, row_metadata)

    if not isinstance(reflection_text, str):
        raise ValueError("reflection_text must be str, dict, or list[dict]")

    return _store_single_reflection(reflection_text, metadata)


def _store_single_reflection(
    reflection_text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Store one reflection record into Qdrant/JSONL fallback."""
    collection_name = "growth_growth"
    fallback_to_jsonl = True

    reflection_id = str(uuid.uuid4())

    if not reflection_text.strip():
        return "Skipped: reflection_text is empty"
    
    if metadata is None:
        metadata = {}
    
    # Add date if not present (store as datetime for reliable range queries)
    if "date" not in metadata:
        metadata["date"] = datetime.now().date()
    else:
        # normalize provided date/datetime to integer timestamp if necessary
        provided = metadata["date"]
        if not isinstance(provided, (datetime, date)):
            if isinstance(provided, str):
                metadata["date"] = datetime.strptime(provided, "%Y-%m-%d").date()
        
    
    # Add reflection text to metadata
    metadata["reflection_text"] = reflection_text
    embedding = get_embedding(reflection_text)
    
    try:        
        client = get_qdrant_client()
        
        # Create point
        point = PointStruct(
            id=reflection_id,
            vector=embedding,
            payload=metadata
        )
        
        # Store in Qdrant
        client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        
        return "Stored in Qdrant with ID: " + reflection_id
        
    except Exception as e:
        # If Qdrant fails and fallback is enabled, write to JSONL
        if fallback_to_jsonl:
            try:
                _write_to_jsonl_fallback(reflection_id, reflection_text, metadata)
                print(f"Warning: Qdrant unavailable, saved to JSONL fallback. Error: {e}")
                return "Stored in JSONL fallback with ID: " + reflection_id
            except Exception as fallback_error:
                raise Exception(f"Both Qdrant and JSONL fallback failed. Qdrant error: {e}, JSONL error: {fallback_error}")
        else:
            raise


def retrieve_reflections(
    query_text: str,
    filter_conditions: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve related reflections from Qdrant using a text query + optional filters.

    Args:
        query_text: Text to embed and use as the similarity query.
        filter_conditions: Optional dict of payload filters. Supported forms:
            - Exact matches: {"strategy": "monthly_revenue_growth_roe"}
            - Date upper-bound: {"date": "YYYY-MM-DD"} will be converted to
              a DatetimeRange lt filter using the provided date string.

    Returns a list of dicts with keys: `id`, `score`, `reflection_text`, `metadata`.

    Raises on Qdrant errors.
    """
    limit = 2
    score_threshold = 0.7
    collection_name = "growth_growth"
    query_embedding = get_embedding(query_text)


    try:
        client = get_qdrant_client()
        
        # Build filter if conditions provided
        # Support simple equality match as well as range queries.
        # For range queries, pass a dict like: {"date": "2024-01-01"}
        search_filter = None
        if filter_conditions:
            must_conditions = []
            for key, value in filter_conditions.items():
                # If key is 'date' and user provided a plain date string or timestamp,
                # treat it as a user-friendly 'lt' (less-than) range and convert to timestamp.
                if key == "date" and isinstance(value, (str)):
                    range_val = datetime.strptime(value, "%Y-%m-%d").date()
                    range_val = value

                    must_conditions.append(FieldCondition(key=key, range=DatetimeRange(lt=range_val)))
                else:
                    # Simple equality match for other fields
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
            search_filter = Filter(must=must_conditions)
        
        query_result = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_filter
        ).points

        # qdrant-client returns QueryResponse with points in newer versions.
        # hits = getattr(query_result, "points", query_result)
        # print(f"Qdrant returned {len(query_result)} hits for query: '{query_text}' with filter: {filter_conditions}")
        # print(f"Raw Qdrant hits: {query_result}")
        # Format results
        header = "## 過往反思\n"
        content = ""
        for hit in query_result:
            content += f"- {hit.payload.get('reflection_text', '')} (score: {hit.score:.4f})\n"
        
        return header + content if content != "" else "沒有找到相似的經驗反思!"
        
    except Exception as e:
        print(f"Error retrieving from Qdrant: {e}")
        raise


def _write_to_jsonl_fallback(
    reflection_id: str,
    reflection_text: str,
    metadata: Dict[str, Any],
    fallback_dir: str = "./data_cache/reflections_fallback"
) -> None:
    """
    寫入 JSONL 備援檔案 (當 Qdrant 不可用時)
    
    Args:
        reflection_id: Reflection ID
        reflection_text: Reflection 文本
        metadata: Metadata
        fallback_dir: 備援檔案目錄
    """
    # Create directory if it doesn't exist
    Path(fallback_dir).mkdir(parents=True, exist_ok=True)
    
    # Append to JSONL file
    fallback_file = Path(fallback_dir) / "reflections_fallback.jsonl"
    
    record = {
        "id": reflection_id,
        "reflection_text": reflection_text,
        "metadata": metadata
    }
    
    with open(fallback_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_collection_stats(collection_name: str = "reflections") -> Dict[str, Any]:
    """
    獲取 collection 的統計資訊
    
    Args:
        collection_name: Collection 名稱，預設為 "reflections"
        
    Returns:
        包含統計資訊的字典
    """
    try:
        client = get_qdrant_client()
        
        collection_info = client.get_collection(collection_name)
        
        return {
            "collection_name": collection_name,
            "vectors_count": collection_info.indexed_vectors_count,
            "points_count": collection_info.points_count,
            "status": collection_info.status
        }
        
    except Exception as e:
        print(f"Error getting collection stats: {e}")
        return {}



def _realistic_samples():
    """Representative production-like reflections and metadata."""
    return [
        {
            "reflection_text": (
                "TSMC monthly revenue grew 23% YoY for two consecutive months, "
                "gross margin stayed above 53%, and AI-related demand from hyperscalers "
                "kept utilization above 90%. Risk is valuation expansion outpacing earnings."
            ),
            "metadata": {
                "strategy": "monthly_revenue_growth_roe",
                "date": "2025-12-20",
            },
            "query": "Semiconductor AI demand and margin sustainability for TSMC",
        },
        {
            "reflection_text": (
                "MediaTek inventory cycle improved, handset mix shifted toward premium chips, "
                "and operating margin stabilized. However, order visibility from Android OEMs "
                "is still volatile, so position sizing should remain moderate."
            ),
            "metadata": {
                "strategy": "quality_growth_pullback",
                "date": "2025-11-15",
            },
            "query": "Inventory normalization and earnings visibility for MediaTek",
        },
        {
            "reflection_text": (
                "TSMC is a very good company with strong fundamentals and growth prospects."
                "However, the stock is currently overvalued and due for a pullback."
                "I would wait for a better entry point before buying."
            ),
            "metadata": {
                "strategy": "monthly_revenue_growth_roe",
                "date": "2025-12-20",
            },
            "query": "Semiconductor AI demand and margin sustainability for TSMC",
        },
    ]


if __name__ == "__main__":
    # Simple smoke test
    from dotenv import load_dotenv
    load_dotenv()


    samples = _realistic_samples()
    result = retrieve_reflections(query_text=samples[0]["query"],filter_conditions={"strategy": "monthly_revenue_growth_roe", "date": "2025-12-31"})
    print(result)
    # store_reflections(reflection_text=samples[2]["reflection_text"], metadata=samples[2]["metadata"])
    # print(get_collection_stats())