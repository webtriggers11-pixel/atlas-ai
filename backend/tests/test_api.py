"""
Phase 3 tests — covers all 6 endpoints with a mocked LLM.
Run from backend/: pytest tests/test_api.py -v
"""
from unittest.mock import patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import get_db
from app.db.base import Base
from app.models import Map, Node, NodeExplanation, Edge  # noqa: F401
from app.llm import ConceptList, Concept
from app.core.config import settings

# ── Test database (same Postgres DB, separate test schema via transactions) ───

engine = create_engine(settings.DATABASE_URL)
TestSession = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def db_session():
    """Each test runs in a transaction that is rolled back on teardown — no data leaks."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestSession(bind=connection)

    app.dependency_overrides[get_db] = lambda: session
    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


client = TestClient(app, raise_server_exceptions=True)

# ── Mock LLM responses ────────────────────────────────────────────────────────

MOCK_CONCEPTS = ConceptList(concepts=[
    Concept(label="Superposition", summary="A qubit exists in multiple states at once until measured."),
    Concept(label="Entanglement", summary="Two qubits become correlated so measuring one instantly determines the other."),
    Concept(label="Quantum gates", summary="Operations that manipulate qubits, analogous to classical logic gates."),
])

MOCK_EXPLANATION = "Quantum computing uses quantum mechanical phenomena to process information exponentially faster than classical computers for certain problems."


# ── Tests ─────────────────────────────────────────────────────────────────────

@patch("app.services.atlas_service.generate_concepts", return_value=MOCK_CONCEPTS)
@patch("app.services.atlas_service.generate_explanation", return_value=MOCK_EXPLANATION)
def test_create_map(mock_exp, mock_concepts):
    """POST /maps returns 201 with nodes and edges."""
    resp = client.post("/maps", json={"topic": "quantum computing", "depth": "standard"})
    assert resp.status_code == 201

    data = resp.json()
    assert data["topic"] == "quantum computing"
    # root node + 3 child nodes
    assert len(data["nodes"]) == 4
    # 3 edges (root → each child)
    assert len(data["edges"]) == 3

    root = next(n for n in data["nodes"] if n["is_root"])
    assert root["label"] == "quantum computing"
    # root explanation pre-populated
    assert len(root["explanations"]) == 1


@patch("app.services.atlas_service.generate_concepts", return_value=MOCK_CONCEPTS)
@patch("app.services.atlas_service.generate_explanation", return_value=MOCK_EXPLANATION)
def test_list_maps(mock_exp, mock_concepts):
    """GET /maps returns created map in the list."""
    client.post("/maps", json={"topic": "quantum computing", "depth": "standard"})
    resp = client.get("/maps")
    assert resp.status_code == 200
    topics = [m["topic"] for m in resp.json()]
    assert "quantum computing" in topics


@patch("app.services.atlas_service.generate_concepts", return_value=MOCK_CONCEPTS)
@patch("app.services.atlas_service.generate_explanation", return_value=MOCK_EXPLANATION)
def test_get_map(mock_exp, mock_concepts):
    """GET /maps/{id} returns the full map."""
    created = client.post("/maps", json={"topic": "quantum computing"}).json()
    resp = client.get(f"/maps/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_map_not_found():
    """GET /maps/{id} with a non-existent id returns 404."""
    resp = client.get(f"/maps/{uuid4()}")
    assert resp.status_code == 404


@patch("app.services.atlas_service.generate_concepts", return_value=MOCK_CONCEPTS)
@patch("app.services.atlas_service.generate_explanation", return_value=MOCK_EXPLANATION)
def test_expand_node(mock_exp, mock_concepts):
    """POST .../expand returns new nodes and edges branching from the target node."""
    created = client.post("/maps", json={"topic": "quantum computing"}).json()
    child = next(n for n in created["nodes"] if not n["is_root"])

    resp = client.post(
        f"/maps/{created['id']}/nodes/{child['id']}/expand",
        json={"depth": "standard"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["new_nodes"]) == 3
    assert len(data["new_edges"]) == 3
    # All new edges originate from the expanded node
    assert all(e["source_node_id"] == child["id"] for e in data["new_edges"])


@patch("app.services.atlas_service.generate_concepts", return_value=MOCK_CONCEPTS)
@patch("app.services.atlas_service.generate_explanation", return_value=MOCK_EXPLANATION)
def test_change_depth_cache_miss_then_hit(mock_exp, mock_concepts):
    """PATCH .../depth calls LLM on first request, returns cache on second — no extra LLM call."""
    created = client.post("/maps", json={"topic": "quantum computing"}).json()
    child = next(n for n in created["nodes"] if not n["is_root"])

    # First call — cache miss, LLM is called
    resp1 = client.patch(
        f"/maps/{created['id']}/nodes/{child['id']}/depth",
        json={"depth": "expert"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["depth"] == "expert"

    call_count_after_first = mock_exp.call_count

    # Second call — cache hit, LLM must NOT be called again
    resp2 = client.patch(
        f"/maps/{created['id']}/nodes/{child['id']}/depth",
        json={"depth": "expert"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["content"] == resp1.json()["content"]
    assert mock_exp.call_count == call_count_after_first  # no extra call


@patch("app.services.atlas_service.generate_concepts", return_value=MOCK_CONCEPTS)
@patch("app.services.atlas_service.generate_explanation", return_value=MOCK_EXPLANATION)
def test_delete_map(mock_exp, mock_concepts):
    """DELETE /maps/{id} returns 204 and the map is gone."""
    created = client.post("/maps", json={"topic": "quantum computing"}).json()
    del_resp = client.delete(f"/maps/{created['id']}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/maps/{created['id']}")
    assert get_resp.status_code == 404
