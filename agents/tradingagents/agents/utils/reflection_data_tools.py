import json
from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor



@tool
def retrieve_reflections(
    query_text: Annotated[
        str,
        (
            "Text query used to search similar historical reflections. "
            "Few-shot examples: "
            "1) 『在景氣下行期，財務體質轉弱但技術面短彈，如何避免誤判反轉？』 "
            "2) 『面對政策利空與供應鏈去庫存時，新聞熱度與基本面背離的處理原則』 "
            "3) 『AI 產業鏈中上游與下游的商業模式風險，如何反映在選股信心分數？』"
        ),
    ],
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
    reflection_text: Annotated[str, "Text query used to search similar historical reflections"] = "",
    strategy: Annotated[str, "Strategy tag for this reflection"] = "",
    end_date: Annotated[str, "End date in yyyy-mm-dd format"] = "",
    metadata_json: Annotated[str, "Optional extra metadata as JSON object string"] = "",
) -> str:
    """
    Store reflections (single or batch) to Qdrant/JSONL fallback.
    - Input format is unified: always pass a JSON list string.
        - Single example: [\"景氣循環末段若看到營收增速下滑、籌碼轉弱與負面政策消息共振，應降低買進信心\"] 
        - Batch example: [\"面對高估值成長股，若財報優於預期且產業需求上修，可接受較高本益比\", "
        "\"技術面突破但新聞來源集中且缺乏基本面支撐時，列為觀察不買進\"]

    Args:
        reflection_text (str): Unified JSON list payload.
        strategy (str): Strategy tag.
        end_date (str): End date in yyyy-mm-dd format.
        metadata_json (str): Optional additional metadata JSON object string.

    Returns:
        str: Storage status message.
    """
    raw_payload = reflection_text.strip()
    if not raw_payload:
        return "reflection_text is required and must be a JSON list string"

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

    try:
        parsed_batch = json.loads(raw_payload)
    except json.JSONDecodeError:
        return "Invalid reflection input: must be a valid JSON list string"

    if not isinstance(parsed_batch, list):
        return "Invalid reflection input: must be a JSON list"

    normalized_batch = []
    for index, row in enumerate(parsed_batch):
        row_text = str(row or "").strip()
        if not row_text:
            return f"Invalid reflection input[{index}]: text is required"
        normalized_batch.append(row_text)

    return route_to_vendor("store_reflections", normalized_batch, metadata or None)
