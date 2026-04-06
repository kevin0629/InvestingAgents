import json
from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor



@tool
def retrieve_reflections(
    query_text: Annotated[str, "Text query used to search similar historical reflections"],
    strategy: Annotated[str, "Optional strategy filter, e.g. monthly_revenue_growth_roe"] = None,
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = None,
) -> str:
    """
    Retrieve historical reflections by semantic similarity with optional filters.

    Args:
        query_text (str): Natural language query used for vector retrieval.
        strategy (str): Optional strategy filter.
        end_date (str): End date in yyyy-mm-dd format.

    Returns:
        str: Formatted reflection summary text.
    """
    filter_conditions = {}
    if strategy:
        filter_conditions["strategy"] = strategy
    if end_date:
        filter_conditions["date"] = end_date

    return route_to_vendor("retrieve_reflections", query_text, filter_conditions or None)


@tool
def store_reflections(
    reflection_text: Annotated[str, "Single reflection text"] = "",
    reflection_texts_json: Annotated[str, "Optional JSON list of reflection texts, e.g. [\"text1\", \"text2\"]"] = "",
    strategy: Annotated[str, "Strategy tag for this reflection"] = "",
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = "",
    metadata_json: Annotated[str, "Optional extra metadata as JSON object string"] = "",
) -> str:
    """
    Store reflections (single or batch) to Qdrant/JSONL fallback.
    - Reflection content can come from:
      1) `reflection_text` for single insert
      2) `reflection_texts_json` for batch insert

    Args:
        reflection_text (str): Single reflection text.
        reflection_texts_json (str): Optional JSON list of reflection texts.
        strategy (str): Strategy tag.
        end_date (str): End date in yyyy-mm-dd format.
        metadata_json (str): Optional additional metadata JSON object string.

    Returns:
        str: Storage status message.
    """
    metadata = {}
    if metadata_json:
        try:
            parsed = json.loads(metadata_json)
            if isinstance(parsed, dict):
                metadata.update(parsed)
        except json.JSONDecodeError:
            # Keep metadata empty on invalid JSON to avoid breaking the tool call.
            pass

    if strategy:
        metadata["strategy"] = strategy
    if end_date:
        metadata["date"] = end_date

    # Batch mode: list of reflection strings with shared metadata.
    if reflection_texts_json:
        try:
            parsed_batch = json.loads(reflection_texts_json)
        except json.JSONDecodeError:
            return "Invalid reflection_texts_json: must be a valid JSON list"

        if not isinstance(parsed_batch, list):
            return "Invalid reflection_texts_json: must be a JSON list"

        normalized_batch = []
        for index, row in enumerate(parsed_batch):
            row_text = str(row or "").strip()
            if not row_text:
                return f"Invalid reflection_texts_json[{index}]: text is required"
            normalized_batch.append(row_text)

        return route_to_vendor("store_reflections", normalized_batch, metadata or None)

    # Single mode.
    if not reflection_text.strip():
        return "reflection_text is required when reflection_texts_json is empty"

    return route_to_vendor("store_reflections", reflection_text, metadata or None)
