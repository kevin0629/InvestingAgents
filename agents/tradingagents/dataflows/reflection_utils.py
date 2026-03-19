import os
import json
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
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
from typing import Union


def get_embedding(text: str) -> List[float]:
    """
    Compute embedding for `text` using provider specified in `DEFAULT_CONFIG`.

    Supported providers use the unified embedding clients:
    - openai -> langchain_openai.OpenAIEmbeddings
    - google/gemini -> langchain_google_genai.GoogleGenerativeAIEmbeddings
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
    """
    獲取 Qdrant 客戶端
    
    Returns:
        QdrantClient instance
        
    Raises:
        ValueError: If QDRANT_URL not configured properly
    """
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if qdrant_api_key:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    else:
        client = QdrantClient(url=qdrant_url)
    
    return client


def store_reflection(
    reflection_text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    儲存 Reflection 到 Qdrant
    
    Args:
        reflection_text: Reflection 文本內容
        metadata: 額外的 metadata，例如 {"strategy": "monthly_revenue_growth_roe", "date": "..."}
        
    Returns:
        儲存的 reflection ID (UUID string)
        
    Raises:
        Exception: If both Qdrant and JSONL fallback fail
    """
    collection_name = "reflections"
    fallback_to_jsonl = True

    reflection_id = str(uuid.uuid4())
    
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
    """
    從 Qdrant 檢索相關的 Reflections
    
    Args:
        query_text: 查詢的文本內容
        filter_conditions: 過濾條件，例如 {"strategy": "monthly_revenue_growth_roe"}，只返回符合條件的 reflections
        
    Returns:
        包含相關 reflections 的列表，每個元素為：
        {
            "id": str,
            "score": float,
            "reflection_text": str,
            "metadata": dict
        }
        
    Raises:
        Exception: If Qdrant query fails
    """
    limit = 5
    score_threshold = 0.7
    collection_name = "reflections"
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
                    print(f"Added range filter for 'date' with lt {range_val} (original value: {value})")
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
        print(f"Qdrant returned {len(query_result)} hits for query: '{query_text}' with filter: {filter_conditions}")
        print(f"Raw Qdrant hits: {query_result}")
        # Format results
        results = []
        for hit in query_result:
            result = {
                "id": hit.id,
                "score": hit.score,
                "reflection_text": hit.payload.get("reflection_text", ""),
                "metadata": {k: v for k, v in hit.payload.items() if k != "reflection_text"}
            }
            results.append(result)
        
        return results
        
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
    # store_reflection(reflection_text=samples[2]["reflection_text"], metadata=samples[2]["metadata"])
    # print(get_collection_stats())