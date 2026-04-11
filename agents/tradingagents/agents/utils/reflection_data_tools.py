import json
from typing import Annotated

from langchain_core.tools import tool

from tradingagents.dataflows.interface import route_to_vendor



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
    filter_conditions = {}
    if strategy:
        filter_conditions["strategy"] = strategy
    if end_date:
        filter_conditions["date"] = end_date

    return route_to_vendor("retrieve_reflections", query_text, filter_conditions or None)


@tool
def store_reflections(
    reflection_text: Annotated[str, "JSON list string of reflection rules to store. Write one reusable rule per item."] = "",
    strategy: Annotated[str, "Strategy tag for these reflections."] = "",
    end_date: Annotated[str, "Optional date in yyyy-mm-dd format."] = "",
    metadata_json: Annotated[str, "Optional metadata JSON object string."] = "",
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
