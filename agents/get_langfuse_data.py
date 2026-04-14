import argparse
import json
import os
from datetime import datetime, timezone
from typing import Any

import requests


def _default_api_url() -> str:
    api_url = os.getenv("LANGFUSE_API_URL")
    if api_url:
        return api_url

    base_url = os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000").rstrip("/")
    return f"{base_url}/api/public/observations"


def _normalize_iso_datetime(value: str) -> str:
    raw = value.strip()
    parse_value = raw

    if raw.endswith("Z"):
        parse_value = raw[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(parse_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime '{value}'. Use ISO-8601 like 2025-04-01T00:00:00Z"
        ) from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.isoformat().replace("+00:00", "Z")


def _build_query_params(
    fields: str | None = None,
    expand_metadata: str | None = None,
    limit: int = 50,
    name: str | None = None,
    user_id: str | None = None,
    observation_type: str | None = None,
    trace_id: str | None = None,
    level: str | None = None,
    parent_observation_id: str | None = None,
    environment: list[str] | None = None,
    from_start_time: str | None = None,
    to_start_time: str | None = None,
    version: str | None = None,
    filter_json: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "limit": limit,
    }

    optional_params = {
        "fields": fields,
        "expandMetadata": expand_metadata,
        "name": name,
        "userId": user_id,
        "type": observation_type,
        "traceId": trace_id,
        "level": level,
        "parentObservationId": parent_observation_id,
        "fromStartTime": from_start_time,
        "toStartTime": to_start_time,
        "version": version,
        "filter": filter_json,
    }

    for key, value in optional_params.items():
        if value is not None and value != "":
            params[key] = value

    if environment:
        params["environment"] = environment

    return params


def get_langfuse_data(
    username: str,
    password: str,
    api_url: str = "http://localhost:3000/api/public/observations",
    max_pages: int = 1,
    **kwargs: Any,
) -> dict[str, Any]:
    """Fetch observations from Langfuse using cursor-based pagination."""
    session = requests.Session()
    session.auth = (username, password)

    params = _build_query_params(**kwargs)

    all_rows: list[dict[str, Any]] = []
    cursor: str | None = None
    page_number = 1
    total_pages: int | None = None
    pagination_mode: str | None = None
    page = 0

    while True:
        page += 1
        if pagination_mode == "cursor":
            if cursor:
                params["cursor"] = cursor
            elif "cursor" in params:
                params.pop("cursor")
            params.pop("page", None)
        elif pagination_mode == "page":
            params["page"] = page_number
            params.pop("cursor", None)
        else:
            params.pop("cursor", None)
            params.pop("page", None)

        response = session.get(api_url, params=params, timeout=30)

        if (
            response.status_code == 501
            and "/api/public/v2/observations" in api_url
            and "only available on Langfuse Cloud" in response.text
        ):
            api_url = api_url.replace("/api/public/v2/observations", "/api/public/observations")
            response = session.get(api_url, params=params, timeout=30)

        # Local/self-hosted versions can reject certain newer query params.
        if response.status_code == 400:
            if "fields" in params:
                retry_params = dict(params)
                retry_params.pop("fields", None)
                response = session.get(api_url, params=retry_params, timeout=30)
                if response.ok:
                    params = retry_params
            if response.status_code == 400 and "expandMetadata" in params:
                retry_params = dict(params)
                retry_params.pop("expandMetadata", None)
                response = session.get(api_url, params=retry_params, timeout=30)
                if response.ok:
                    params = retry_params

        if not response.ok:
            raise requests.HTTPError(
                f"Langfuse request failed: {response.status_code} {response.reason}; "
                f"url={response.url}; body={response.text}",
                response=response,
            )

        payload = response.json()
        page_data = payload.get("data", [])
        meta = payload.get("meta", {})

        if pagination_mode is None:
            if "cursor" in meta:
                pagination_mode = "cursor"
            elif "page" in meta and "totalPages" in meta:
                pagination_mode = "page"
            else:
                pagination_mode = "single"

        if pagination_mode == "cursor":
            cursor = meta.get("cursor")
        elif pagination_mode == "page":
            total_pages = int(meta.get("totalPages", page_number))
            page_number += 1

        if page_data:
            all_rows.extend(page_data)

        if pagination_mode == "cursor":
            is_done = (not cursor) or (page >= max_pages)
        elif pagination_mode == "page":
            is_done = (total_pages is not None and page_number > total_pages) or (page >= max_pages)
        else:
            is_done = True

        if is_done:
            return {
                "data": all_rows,
                "meta": {
                    "apiUrl": api_url,
                    "paginationMode": pagination_mode,
                    "lastCursor": cursor,
                    "pagesFetched": page,
                    "rowsFetched": len(all_rows),
                },
            }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Langfuse observations")
    parser.add_argument("--api-url", default=_default_api_url())
    parser.add_argument("--username", default=os.getenv("LANGFUSE_USERNAME") or os.getenv("LANGFUSE_PUBLIC_KEY"))
    parser.add_argument("--password", default=os.getenv("LANGFUSE_PASSWORD") or os.getenv("LANGFUSE_SECRET_KEY"))
    parser.add_argument("--fields", default=None)
    parser.add_argument("--expand-metadata")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--name")
    parser.add_argument("--user-id")
    parser.add_argument("--type", dest="observation_type")
    parser.add_argument("--trace-id")
    parser.add_argument("--level", choices=["DEBUG", "DEFAULT", "WARNING", "ERROR"])
    parser.add_argument("--parent-observation-id")
    parser.add_argument("--environment", action="append")
    parser.add_argument("--from-start-time", type=_normalize_iso_datetime, help="ISO-8601 datetime")
    parser.add_argument("--to-start-time", type=_normalize_iso_datetime, help="ISO-8601 datetime")
    parser.add_argument("--version")
    parser.add_argument("--filter-json", help="JSON string per Langfuse filter schema")
    parser.add_argument("--output", default="langfuse_observations.json")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if not args.username or not args.password:
        raise ValueError("Please provide LANGFUSE_USERNAME and LANGFUSE_PASSWORD via env vars or CLI args")

    result = get_langfuse_data(
        username=args.username,
        password=args.password,
        api_url=args.api_url,
        max_pages=args.max_pages,
        fields=args.fields,
        expand_metadata=args.expand_metadata,
        limit=args.limit,
        name=args.name,
        user_id=args.user_id,
        observation_type=args.observation_type,
        trace_id=args.trace_id,
        level=args.level,
        parent_observation_id=args.parent_observation_id,
        environment=args.environment,
        from_start_time=args.from_start_time,
        to_start_time=args.to_start_time,
        version=args.version,
        filter_json=args.filter_json,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Fetched {result['meta']['rowsFetched']} observations into {args.output}")