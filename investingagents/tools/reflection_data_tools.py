import os
import uuid
import json
from typing import Annotated, Optional, Dict, Any, List, Union
from datetime import datetime, date
from langchain_core.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    DatetimeRange,
)
from functools import lru_cache
from .config import get_config
from embedding_client import create_embedding_client



COLLECTION_NAME = "reflections"

def get_embedding(text: str) -> List[float]:
    """Compute embedding for `text` using provider specified in `default_config`.

    Notes:
    - The function selects an embedding client by `default_config['embedding_provider']`.
    - For OpenAI it requests a 1536-dimension embedding (`text-embedding-3-small`).
    - For Google/Gemini it requests a 1536-dimension embedding (`gemini-embedding-001`).
    - Returns a list of floats representing the vector embedding.
    """
    config = get_config()
    
    kwargs = {}
    provider = config.get("embedding_provider", "openai")
    if provider == "openai":
        model = config.get("openai_embedding_model", "text-embedding-3-small")
        kwargs = {"dimensions": 1536}
    elif provider in ("google"):
        model = config.get("gemini_embedding_model", "gemini-embedding-001")
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

@tool
def store_reflections(
    reflection_text: Annotated[str, "JSON list string of reflection rules to store. Write one reusable rule per item."] = "",
    strategy: Annotated[str, "Strategy tag for these reflections."] = "",
    end_date: Annotated[str, "Optional date in yyyy-mm-dd format."] = "",
) -> str:
    """
    Store reflections (single or batch) to Qdrant/JSONL fallback.

    Writing guide (to improve future retrieval quality):
    - Use generalized, reusable rules instead of stock-specific narratives.
    - Prefer "condition -> action" format.
    - Keep one rule per list item.

    Unified payload format (always JSON list string):
    - Single: [\"景氣循環末段若營收增速下滑且籌碼轉弱，應降低買進信心\"]
    - Batch: [\"高估值成長股若需求下修，先降低部位再等待確認\", \"技術突破但缺乏基本面支撐時，列為觀察不追價\"]

    Args:
        reflection_text (str): Unified JSON list payload.
        strategy (str): Strategy tag.
        end_date (str): End date in yyyy-mm-dd format.

    Returns:
        str: Storage status message.
    """
    raw_payload = reflection_text.strip()
    if not raw_payload:
        return "reflection_text is required and must be a JSON list string"
    
    try:
        parsed_batch = json.loads(raw_payload)
    except json.JSONDecodeError:
        return "Invalid JSON format for reflection_text"

    if not isinstance(parsed_batch, list):
        return "Invalid reflection input: must be a JSON list"
    
    normalized_batch = []
    for index, row in enumerate(parsed_batch):
        row_text = ""
        if isinstance(row, str):
            row_text = row.strip()
        if not row_text:
            return f"Invalid reflection input[{index}]: text is required"
        normalized_batch.append(row_text)

    metadata = {}
    if end_date != "":
        metadata["date"] = datetime.strptime(end_date, "%Y-%m-%d").date()
    if strategy != "":
        metadata["strategy"] = strategy

    for text in normalized_batch:
        _store_single_reflection(text, metadata)

    return f"Store completed!"


def _store_single_reflection(
    reflection_text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Store one reflection record into Qdrant."""
    collection_name = COLLECTION_NAME

    reflection_id = str(uuid.uuid4())

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

    except Exception as e:
        raise Exception(f"Qdrant failed. Qdrant error: {e}")
    
    return "Stored in Qdrant with ID: " + reflection_id



@tool
def retrieve_reflections(
    query_text: Annotated[str, "Natural-language query for retrieving similar reflection rules. Prefer generic decision rules (not single-stock details)."],
    strategy: Annotated[str, "Optional strategy filter, e.g. monthly_revenue_growth_roe."] = None,
    end_date: Annotated[str, "Optional date filter in yyyy-mm-dd format."] = None,
) -> str:
    """
    Retrieve historical reflections by semantic similarity with optional filters.

    Query writing guide:
    - Focus on reusable rules, not one-off stock events.
    - Include condition + action to improve matching quality.
    - Keep wording concrete and concise.

    Good query examples:
    1) 在景氣下行期，財務轉弱但技術反彈時，如何避免誤判反轉？
    2) 當新聞熱度上升但基本面未改善時，應如何調整買進信心？
    3) 高估值成長股在需求下修時，倉位與進場條件怎麼設定？

    Args:
        query_text (str): Natural language query used for vector retrieval.
        strategy (str): Optional strategy filter.
        end_date (str): End date in yyyy-mm-dd format.

    Returns:
        str: Formatted reflection summary text.
    """
    limit = 2
    score_threshold = 0.7
    collection_name = COLLECTION_NAME
    query_embedding = get_embedding(query_text)

    try: 
        client = get_qdrant_client()
        must_conditions = []
            
        if strategy:
            must_conditions.append(FieldCondition(key="strategy", match=MatchValue(value=strategy)))
            
        if end_date:
            must_conditions.append(FieldCondition(key="date", range=DatetimeRange(lt=datetime.strptime(end_date, "%Y-%m-%d").date())))

        search_filter = Filter(must=must_conditions)
            
        query_result = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_filter
        ).points
    except Exception as e:
        raise Exception(f"Qdrant failed. Qdrant error: {e}")

    header = "## 過往反思\n"
    content = ""
    for hit in query_result:
        content += f"- {hit.payload.get('reflection_text', '')} (score: {hit.score:.4f})\n"
        
    return header + content if content != "" else "沒有找到相似的經驗反思!"


def get_collection_stats(collection_name: str = COLLECTION_NAME) -> Dict[str, Any]:
    """
    獲取 collection 的統計資訊
    
    Args:
        collection_name: Collection 名稱
        
    Returns:
        包含統計資訊的字典
    """
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name)

    except Exception as e:
        raise Exception(f"Failed to get collection stats. Qdrant error: {e}")
        
    return {
        "collection_name": collection_name,
        "vectors_count": collection_info.indexed_vectors_count,
        "points_count": collection_info.points_count,
        "status": collection_info.status
    }