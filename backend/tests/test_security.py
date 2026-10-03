"""
V2 Phase 12 — security: optional auth, ownership isolation, rate limiting, headers, CORS, upload hardening.
Run from backend/: pytest tests/test_security.py -v
"""
import io
import zipfile

import pytest

from app.core import security
from app.core.config import settings
from app.services.extraction import DocumentError, detect_file_type, safe_filename

STRONG_SECRET = "x" * 48


@pytest.fixture
def auth_on(monkeypatch):
    """Turn on hosted mode (login required) with a strong signing secret."""
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "AUTH_ALLOW_REGISTRATION", True)
    monkeypatch.setattr(settings, "JWT_SECRET", STRONG_SECRET)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)


def _register(client, email) -> dict:
    """Register a user and return Authorization headers for them."""
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": "correct horse battery"})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ── Auth off (self-hosted default) ────────────────────────────────────────────

def test_auth_off_by_default_everything_open(client):
    """No login needed and the auth endpoints are hidden when AUTH_ENABLED=false."""
    assert client.get("/api/v1/auth/status").json() == {"enabled": False, "registration": True}
    assert client.get("/api/v1/projects").status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "a@b.co", "password": "whatever123"}).status_code == 404


# ── Auth on (hosted) ──────────────────────────────────────────────────────────

def test_protected_routes_need_a_token(client, auth_on):
    """Without a token: 401 on V2 and V1 routes; health and status stay public."""
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/settings").status_code == 401
    assert client.get("/api/v1/documents").status_code == 401
    assert client.get("/maps").status_code == 401          # v1 topic explorer is protected too
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/auth/status").json()["enabled"] is True


def test_register_login_me_flow(client, auth_on):
    """Register → login → /me; email is normalized; duplicates and wrong passwords are refused."""
    headers = _register(client, "  Vipul@Example.com ")
    assert client.get("/api/v1/auth/me", headers=headers).json() == {"email": "vipul@example.com"}
    assert client.post("/api/v1/auth/register",
                       json={"email": "vipul@example.com", "password": "another password"}).status_code == 409
    good = client.post("/api/v1/auth/login", json={"email": "vipul@example.com", "password": "correct horse battery"})
    assert good.status_code == 200 and good.json()["token"]
    bad = client.post("/api/v1/auth/login", json={"email": "vipul@example.com", "password": "wrong password"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong password"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()          # no hint about which emails have accounts


def test_password_is_hashed_never_stored(client, db, auth_on):
    """The users table holds a bcrypt hash, not the password."""
    from app.models import User
    _register(client, "hash@example.com")
    user = db.query(User).filter_by(email="hash@example.com").one()
    assert user.password_hash.startswith("$2") and "correct horse" not in user.password_hash


def test_registration_can_be_closed(client, auth_on, monkeypatch):
    """AUTH_ALLOW_REGISTRATION=false → 403 on register."""
    monkeypatch.setattr(settings, "AUTH_ALLOW_REGISTRATION", False)
    resp = client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "long enough pw"})
    assert resp.status_code == 403


def test_tampered_expired_and_alg_none_tokens_rejected(client, auth_on, monkeypatch):
    """Signature, expiry and algorithm are all enforced."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    headers = _register(client, "tok@example.com")
    token = headers["Authorization"].split()[1]
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    expired = jwt.encode({"sub": str(uuid4()), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         STRONG_SECRET, algorithm="HS256")
    unsigned = jwt.encode({"sub": str(uuid4())}, key=None, algorithm="none")
    other_key = jwt.encode({"sub": str(uuid4())}, "y" * 48, algorithm="HS256")
    for bad in (tampered, expired, unsigned, other_key, "not-a-jwt"):
        assert client.get("/api/v1/projects", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_weak_jwt_secret_refused(client, auth_on, monkeypatch):
    """A default/short secret makes auth fail closed instead of signing forgeable tokens."""
    monkeypatch.setattr(settings, "JWT_SECRET", "change-me")
    resp = client.post("/api/v1/auth/register", json={"email": "w@example.com", "password": "long enough pw"})
    assert resp.status_code == 500 and "JWT_SECRET" in resp.json()["detail"]


def test_users_only_see_their_own_analyses(client, db, auth_on):
    """User B can't list, read, change or ask about user A's analysis — and gets 404, not 403."""
    alice, bob = _register(client, "alice@example.com"), _register(client, "bob@example.com")
    pid = client.post("/api/v1/projects", json={"name": "Alice's review"}, headers=alice).json()["id"]

    assert [p["id"] for p in client.get("/api/v1/projects", headers=alice).json()] == [pid]
    assert client.get("/api/v1/projects", headers=bob).json() == []
    assert client.get(f"/api/v1/projects/{pid}", headers=bob).status_code == 404
    assert client.patch(f"/api/v1/projects/{pid}", json={"name": "pwned"}, headers=bob).status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/requirements", headers=bob).status_code == 404
    assert client.post(f"/api/v1/projects/{pid}/chat", json={"message": "what is missing?"},
                       headers=bob).status_code == 404
    assert client.delete(f"/api/v1/projects/{pid}", headers=bob).status_code == 404
    assert client.get(f"/api/v1/projects/{pid}", headers=alice).json()["name"] == "Alice's review"


def test_child_resources_are_owner_checked(client, db, auth_on):
    """Documents, requirements, runs and findings are checked through their analysis."""
    from tests.test_projects_api import _document
    from app.models import AnalysisRun, Finding, Requirement

    alice, bob = _register(client, "a2@example.com"), _register(client, "b2@example.com")
    pid = client.post("/api/v1/projects", json={"name": "Private"}, headers=alice).json()["id"]
    doc = _document(db, pid)
    req = Requirement(project_id=pid, code="REQ-001", text="Must log in.", status="approved",
                      origin="manual", content_hash="h")
    db.add(req)
    db.flush()
    run = AnalysisRun(project_id=pid, status="completed")
    db.add(run)
    db.flush()
    finding = Finding(run_id=run.id, requirement_id=req.id, status="missing", confidence=0.5, explanation="x" * 30)
    db.add(finding)
    db.flush()

    for url in (f"/api/v1/documents/{doc.id}", f"/api/v1/documents/{doc.id}/chunks",
                f"/api/v1/runs/{run.id}", f"/api/v1/runs/{run.id}/findings", f"/api/v1/runs/{run.id}/report",
                f"/api/v1/runs/{run.id}/export?format=csv",
                f"/api/v1/findings/{finding.id}", f"/api/v1/findings/{finding.id}/traces"):
        assert client.get(url, headers=bob).status_code == 404, url
        assert client.get(url, headers=alice).status_code == 200, url
    assert client.patch(f"/api/v1/requirements/{req.id}", json={"status": "rejected"}, headers=bob).status_code == 404
    assert client.post(f"/api/v1/findings/{finding.id}/investigate", headers=bob).status_code == 404
    assert client.post(f"/api/v1/runs/{run.id}/investigate", headers=bob).status_code == 404
    assert client.delete(f"/api/v1/documents/{doc.id}", headers=bob).status_code == 404
    assert client.get("/api/v1/documents", headers=bob).json() == []
    assert [d["id"] for d in client.get("/api/v1/documents", headers=alice).json()] == [str(doc.id)]


# ── Rate limiting ─────────────────────────────────────────────────────────────

def test_llm_endpoints_are_rate_limited(client, monkeypatch):
    """Past the per-minute limit an LLM endpoint answers 429 with Retry-After, before doing any work."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(security, "_store", security._RateStore())
    monkeypatch.setattr(security._store, "_redis_down_until", float("inf"))   # isolated in-memory counters
    from tests.test_projects_api import _project
    pid = _project(client)["id"]

    codes = [client.post(f"/api/v1/projects/{pid}/analyze").status_code
             for _ in range(settings.RATE_LIMIT_LLM_PER_MINUTE + 2)]
    assert 429 not in codes[: settings.RATE_LIMIT_LLM_PER_MINUTE]
    assert codes[-1] == 429
    blocked = client.post(f"/api/v1/projects/{pid}/analyze")
    assert int(blocked.headers["Retry-After"]) >= 1
    assert client.get(f"/api/v1/projects/{pid}").status_code == 200   # reads are not limited


def test_rate_limit_counts_per_client():
    """Different clients get separate counters."""
    store = security._RateStore()
    store._redis_down_until = float("inf")
    for _ in range(3):
        store.hit("rl:t:ip:1", 60)
    assert store.hit("rl:t:ip:1", 60)[0] == 4
    assert store.hit("rl:t:ip:2", 60)[0] == 1


def test_forwarded_ip_trusted_only_from_proxy(monkeypatch):
    """X-Forwarded-For is honoured from our own proxy (loopback) but not from a random client."""
    from starlette.requests import Request

    def request(peer):
        """Build a bare request from `peer` claiming to forward for 9.9.9.9."""
        return Request({"type": "http", "client": (peer, 1234), "headers": [(b"x-forwarded-for", b"9.9.9.9, 10.0.0.1")]})

    # "9.9.9.9" was sent by the client (forgeable); "10.0.0.1" was appended by our proxy
    assert security.client_ip(request("127.0.0.1")) == "10.0.0.1"
    assert security.client_ip(request("203.0.113.5")) == "203.0.113.5"
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert security.client_ip(request("172.18.0.1")) == "10.0.0.1"


# ── Headers and CORS ──────────────────────────────────────────────────────────

def test_security_headers_present(client):
    """Every response carries the hardening headers."""
    headers = client.get("/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "no-referrer"


def test_cors_allows_only_configured_origins(client):
    """A configured origin gets CORS headers; an unknown site does not."""
    allowed = settings.CORS_ORIGINS.split(",")[0].strip()
    ok = client.options("/api/v1/projects", headers={"Origin": allowed, "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == allowed
    evil = client.options("/api/v1/projects",
                          headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in evil.headers


# ── Upload hardening ──────────────────────────────────────────────────────────

def test_filenames_are_sanitized():
    """Directory parts and control characters are stripped from display names."""
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("C:\\Users\\x\\evil.pdf") == "evil.pdf"
    assert safe_filename("a\x00b\nc.pdf") == "abc.pdf"
    assert safe_filename("") == "document"
    assert len(safe_filename("a" * 400 + ".pdf")) == 255


def test_docx_zip_bomb_rejected():
    """A DOCX that would expand past the limit is refused before parsing."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"\0" * (101 * 1024 * 1024))   # compresses to ~100 KB
    with pytest.raises(DocumentError, match="expands to more than"):
        detect_file_type("bomb.docx", buffer.getvalue())


def test_corrupt_docx_rejected():
    """Zip magic bytes but no valid archive → clear error."""
    with pytest.raises(DocumentError, match="corrupt"):
        detect_file_type("bad.docx", b"PK\x03\x04" + b"garbage" * 10)
