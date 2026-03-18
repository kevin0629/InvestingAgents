import time
from types import SimpleNamespace
import pytest

from qdrant_client.models import FieldCondition, MatchValue, Range

import agents.tradingagents.dataflows.reflection_utils as ru


class FakeClient:
    def __init__(self):
        self.upsert_called = False
        self.upsert_points = None
        self.last_query_filter = None
        self.retrieved_ids = []
        self.deleted_ids = []

    def get_collection(self, name):
        # pretend collection exists
        return SimpleNamespace(vectors_count=0, points_count=0, status="ok")

    def create_collection(self, collection_name, vectors_config):
        # no-op for tests
        return True

    def upsert(self, collection_name, points):
        self.upsert_called = True
        self.upsert_points = points

    def search(self, collection_name, query_vector, limit, score_threshold, query_filter):
        # capture filter for assertions and return fake hits
        self.last_query_filter = query_filter
        # return two fake hits
        return [
            SimpleNamespace(id="id1", score=0.95, payload={"reflection_text": "r1", "strategy": "monthly_revenue_growth_roe", "date": query_filter.must[0].range.lt if hasattr(query_filter, 'must') and query_filter.must else None}),
            SimpleNamespace(id="id2", score=0.9, payload={"reflection_text": "r2", "strategy": "other"}),
        ]

    def retrieve(self, collection_name, ids):
        # return fake point objects with payload
        pts = []
        for i in ids:
            pts.append(SimpleNamespace(id=i, payload={"reflection_text": "test", "date": int(time.time())}))
        return pts

    def delete(self, collection_name, points_selector):
        self.deleted_ids.extend(points_selector)
        return True


@pytest.fixture(autouse=True)
def patch_get_client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(ru, "get_qdrant_client", lambda: fake)
    return fake


def test_store_reflection_converts_date_and_upserts(patch_get_client):
    fake = patch_get_client
    # provide ISO date string
    meta = {"date": "2024-01-01", "strategy": "monthly_revenue_growth_roe"}
    emb = [0.1] * 10

    res = ru.store_reflection("hello", emb, metadata=meta)

    assert fake.upsert_called
    assert fake.upsert_points is not None
    # payload is stored in PointStruct; the upsert points list should contain at least one element with payload
    payload = fake.upsert_points[0].payload
    assert payload["strategy"] == "monthly_revenue_growth_roe"
    assert isinstance(payload["date"], int)


def test_retrieve_reflections_builds_date_lt_filter_and_returns_results(patch_get_client):
    fake = patch_get_client
    # call with strategy equality and date string
    q_emb = [0.0] * 10
    results = ru.retrieve_reflections(q_emb, {"strategy": "monthly_revenue_growth_roe", "date": "2024-01-01"})

    # verify search returned formatted results
    assert isinstance(results, list)
    assert any(r["metadata"].get("strategy") == "monthly_revenue_growth_roe" for r in results)

    # verify that the client captured a Filter with a date range lt
    qf = fake.last_query_filter
    assert qf is not None
    # must contain a FieldCondition for 'date' and one for 'strategy'
    keys = [c.key for c in qf.must]
    assert "date" in keys
    assert "strategy" in keys


def test_get_reflection_by_id_and_delete(patch_get_client):
    fake = patch_get_client
    # test retrieve by id
    rid = "some-id"
    res = ru.get_reflection_by_id(rid)
    assert res is not None
    assert res["id"] == rid

    # test delete
    ok = ru.delete_reflection(rid)
    assert ok
    assert rid in fake.deleted_ids
