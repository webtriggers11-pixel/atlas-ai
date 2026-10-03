"""
Security building blocks (Phase 12):
- per-client rate limiting (Redis, with an in-process fallback)
- security headers middleware
- optional authentication: password hashing, JWT tokens, the current user, and ownership checks

Authentication is OFF by default (AUTH_ENABLED=false): a self-hosted install works without
logins. When it is on, every V2 endpoint requires a valid token and every analysis is visible
only to the user who created it.
"""
import contextvars
import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Client identity ─────────────────────────────────────────────────────────────

def client_ip(request: Request) -> str:
    """The caller's IP. Behind our own reverse proxy (loopback peer, or TRUST_PROXY_HEADERS) use X-Forwarded-For.

    The LAST entry is the one our proxy appended; earlier entries come from the client and can be forged.
    """
    host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and (host in ("127.0.0.1", "::1", "localhost") or settings.TRUST_PROXY_HEADERS):
        return forwarded.split(",")[-1].strip() or host
    return host


# ── Rate limiting ───────────────────────────────────────────────────────────────

class _RateStore:
    """Fixed-window counters: Redis when reachable (shared by all API processes), else in-process memory."""

    def __init__(self):
        """Lazy Redis connection with a short timeout and a cool-off after failures."""
        self._redis = None
        self._redis_down_until = 0.0
        self._memory: dict[str, tuple[int, float]] = {}

    def _client(self):
        """A Redis client, or None while Redis is known to be unreachable."""
        if time.monotonic() < self._redis_down_until:
            return None
        if self._redis is None:
            import redis
            self._redis = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.3, socket_timeout=0.3)
        return self._redis

    def hit(self, key: str, window_s: int) -> tuple[int, int]:
        """Count one request; return (count in current window, seconds until the window resets)."""
        client = self._client()
        if client is not None:
            try:
                pipe = client.pipeline()
                pipe.incr(key)
                pipe.expire(key, window_s, nx=True)
                pipe.ttl(key)
                count, _, ttl = pipe.execute()
                return int(count), max(int(ttl), 1)
            except Exception as exc:   # Redis down: degrade to per-process limits, retry Redis in a minute
                logger.warning("Rate limiter falling back to memory: %s", exc)
                self._redis_down_until = time.monotonic() + 60
        now = time.monotonic()
        count, reset = self._memory.get(key, (0, now + window_s))
        if now >= reset:
            count, reset = 0, now + window_s
        self._memory[key] = (count + 1, reset)
        return count + 1, max(int(reset - now), 1)


_store = _RateStore()


def rate_limit(bucket: str, per_minute: int):
    """FastAPI dependency: allow `per_minute` requests per client per bucket, else 429 with Retry-After."""

    def check(request: Request):
        """Count this request and reject it if the client is over the limit."""
        if not settings.RATE_LIMIT_ENABLED:
            return
        user = current_user_id.get()
        who = f"user:{user}" if user else f"ip:{client_ip(request)}"
        count, retry_after = _store.hit(f"rl:{bucket}:{who}:{int(time.time() // 60)}", 60)
        if count > per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests — limit is {per_minute} per minute for this action. Try again in {retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )

    return check


# Limits for actions that call the LLM (cost) or do heavy processing
llm_limit = rate_limit("llm", per_minute=settings.RATE_LIMIT_LLM_PER_MINUTE)
upload_limit = rate_limit("upload", per_minute=settings.RATE_LIMIT_UPLOADS_PER_MINUTE)


# ── Security headers ────────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Conservative headers for an API that only serves JSON and file downloads."""

    async def dispatch(self, request, call_next):
        """Add the headers to every response."""
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return response


# ── Optional authentication ─────────────────────────────────────────────────────

# The authenticated user's id for this request (None when auth is off or for public routes)
current_user_id: contextvars.ContextVar[UUID | None] = contextvars.ContextVar("current_user_id", default=None)

_bearer = HTTPBearer(auto_error=False)
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """bcrypt hash (salted, slow by design)."""
    import bcrypt
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Constant-time bcrypt check."""
    import bcrypt
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _secret() -> str:
    """The JWT signing secret — refuse weak/missing secrets when auth is enabled."""
    secret = settings.JWT_SECRET
    if len(secret) < 32 or secret.startswith("change-me"):
        raise HTTPException(status_code=500, detail="Server misconfigured: set a strong JWT_SECRET (32+ characters).")
    return secret


def create_token(user_id: UUID) -> str:
    """Signed JWT for a user, valid for JWT_EXPIRE_HOURS."""
    import jwt
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=settings.JWT_EXPIRE_HOURS)}
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def _decode(token: str) -> UUID:
    """Validate a token and return its user id (401 on anything wrong)."""
    import jwt
    try:
        payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])   # pinned algorithm: no "alg: none" tricks
        return UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired session — please sign in again.",
                            headers={"WWW-Authenticate": "Bearer"})


async def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> UUID | None:
    """Router-level dependency: when auth is on, require a valid bearer token and remember the user.

    async on purpose: a sync dependency runs in a worker thread, and a contextvar set there would not
    be visible to the endpoint. Set here (in the request's task), it is copied into the endpoint's thread.
    """
    if not settings.AUTH_ENABLED:
        current_user_id.set(None)
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in required.", headers={"WWW-Authenticate": "Bearer"})
    user_id = _decode(credentials.credentials)
    current_user_id.set(user_id)
    return user_id


def ensure_owner(owner_id: UUID | None) -> None:
    """With auth on, a resource is visible only to its owner. Answer 404 (not 403) so ids can't be probed."""
    if not settings.AUTH_ENABLED:
        return
    user = current_user_id.get()
    if user is None or owner_id != user:
        raise HTTPException(status_code=404, detail="Not found.")
