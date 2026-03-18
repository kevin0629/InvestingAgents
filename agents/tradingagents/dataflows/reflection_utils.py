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
    SearchRequest,
    Range,
)
from pathlib import Path
from functools import lru_cache
from agents.tradingagents.default_config import DEFAULT_CONFIG
from agents.tradingagents.embedding_client import create_embedding_client
from typing import Union


def get_embedding(text: str) -> List[float]:
    """
    Compute embedding for `text` using provider specified in `DEFAULT_CONFIG`.

    Supported providers use the unified embedding clients:
    - openai -> langchain_openai.OpenAIEmbeddings
    - google/gemini -> langchain_google_genai.GoogleGenerativeAIEmbeddings
    """
    provider = DEFAULT_CONFIG.get("embedding_provider", "openai")
    if provider == "openai":
        model = DEFAULT_CONFIG.get("openai_embedding_model", "text-embedding-3-small")
    elif provider in ("google", "gemini"):
        model = DEFAULT_CONFIG.get("gemini_embedding_model", "gemini-embedding-001")
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")

    embedding_client = create_embedding_client(provider=provider, model=model)
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


def ensure_collection_exists(
    collection_name: str = "reflections",
    vector_size: int = 1536,
    distance: Distance = Distance.COSINE
) -> None:
    """
    確保 Qdrant collection 存在，如果不存在則創建
    
    Args:
        collection_name: Collection 名稱，預設為 "reflections"
        vector_size: 向量維度，預設 1536 (OpenAI embedding size)
        distance: 距離計算方式，預設 COSINE
    """
    client = get_qdrant_client()
    
    try:
        client.get_collection(collection_name)
    except Exception:
        # Collection doesn't exist, create it
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance),
        )


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
    
    # Add date if not present (store as integer timestamp for reliable range queries)
    if "date" not in metadata:
        metadata["date"] = int(datetime.now().timestamp())
    else:
        # normalize provided date/datetime to integer timestamp if necessary
        provided = metadata["date"]
        if isinstance(provided, (datetime, date)):
            if isinstance(provided, date) and not isinstance(provided, datetime):
                provided = datetime.combine(provided, datetime.min.time())
            metadata["date"] = int(provided.timestamp())
        else:
            # if string or numeric, try to parse ISO date strings into timestamp
            try:
                if isinstance(provided, str):
                    parsed = datetime.fromisoformat(provided)
                    metadata["date"] = int(parsed.timestamp())
            except Exception:
                # leave value as provided (could already be an int timestamp)
                pass
        
    
    # Add reflection text to metadata
    metadata["reflection_text"] = reflection_text
    embedding = get_embedding(reflection_text)
    
    try:
        # Ensure collection exists
        ensure_collection_exists(collection_name=collection_name, vector_size=len(embedding))
        
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
                if key == "date" and isinstance(value, (str, int, float)):
                    try:
                        if isinstance(value, (int, float)):
                            range_val = int(value)
                        else:
                            # try ISO parse first, fallback to YYYY-MM-DD
                            try:
                                parsed = datetime.fromisoformat(value)
                            except Exception:
                                parsed = datetime.strptime(value, "%Y-%m-%d")
                            range_val = int(parsed.timestamp())
                    except Exception:
                        range_val = value

                    must_conditions.append(FieldCondition(key=key, range=Range(lt=range_val)))
                else:
                    # Simple equality match for other fields
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
            search_filter = Filter(must=must_conditions)
        
        # Search
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_filter
        )
        
        # Format results
        results = []
        for hit in search_result:
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


def get_reflection_by_id(
    reflection_id: str,
    collection_name: str = "reflections"
) -> Optional[Dict[str, Any]]:
    """
    根據 ID 獲取特定的 Reflection
    
    Args:
        reflection_id: Reflection 的 UUID
        collection_name: Collection 名稱，預設為 "reflections"
        
    Returns:
        包含 reflection 資料的字典，如果不存在則返回 None
        {
            "id": str,
            "reflection_text": str,
            "metadata": dict
        }
    """
    try:
        client = get_qdrant_client()
        
        points = client.retrieve(
            collection_name=collection_name,
            ids=[reflection_id]
        )
        
        if not points:
            return None
        
        point = points[0]
        return {
            "id": point.id,
            "reflection_text": point.payload.get("reflection_text", ""),
            "metadata": {k: v for k, v in point.payload.items() if k != "reflection_text"}
        }
        
    except Exception as e:
        print(f"Error retrieving reflection by ID: {e}")
        return None


def delete_reflection(
    reflection_id: str,
    collection_name: str = "reflections"
) -> bool:
    """
    刪除指定的 Reflection
    
    Args:
        reflection_id: Reflection 的 UUID
        collection_name: Collection 名稱，預設為 "reflections"
        
    Returns:
        是否成功刪除
    """
    try:
        client = get_qdrant_client()
        
        client.delete(
            collection_name=collection_name,
            points_selector=[reflection_id]
        )
        
        return True
        
    except Exception as e:
        print(f"Error deleting reflection: {e}")
        return False


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
            "vectors_count": collection_info.vectors_count,
            "points_count": collection_info.points_count,
            "status": collection_info.status
        }
        
    except Exception as e:
        print(f"Error getting collection stats: {e}")
        return {}
