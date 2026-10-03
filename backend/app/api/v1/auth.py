import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import authenticate, create_token, hash_password, rate_limit, verify_password
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
login_limit = rate_limit("login", per_minute=10)   # slows down password guessing


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        """Lower-case and validate the email shape."""
        value = value.strip().lower()
        if not _EMAIL.match(value):
            raise ValueError("enter a valid email address")
        return value


class TokenResponse(BaseModel):
    token: str
    email: str


class AuthStatus(BaseModel):
    enabled: bool
    registration: bool


def _require_enabled():
    """Auth endpoints exist only in hosted mode."""
    if not settings.AUTH_ENABLED:
        raise HTTPException(status_code=404, detail="Authentication is disabled on this server.")


# GET /api/v1/auth/status
# Example response: {"enabled": false, "registration": true}
@router.get("/status", response_model=AuthStatus)
def auth_status():
    """Whether this server requires sign-in (the UI shows a login screen only if it does)."""
    return AuthStatus(enabled=settings.AUTH_ENABLED, registration=settings.AUTH_ALLOW_REGISTRATION)


# POST /api/v1/auth/register
# Example request:  {"email": "vipul@example.com", "password": "a long passphrase"}
# Example response: 201 {"token": "<jwt>", "email": "vipul@example.com"}
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(_require_enabled), Depends(login_limit)])
def register(body: Credentials, db: Session = Depends(get_db)):
    """Create an account and sign in."""
    if not settings.AUTH_ALLOW_REGISTRATION:
        raise HTTPException(status_code=403, detail="Registration is closed on this server.")
    if db.execute(select(User).where(User.email == body.email)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return TokenResponse(token=create_token(user.id), email=user.email)


# POST /api/v1/auth/login
# Example request:  {"email": "vipul@example.com", "password": "a long passphrase"}
# Example response: {"token": "<jwt>", "email": "vipul@example.com"}
@router.post("/login", response_model=TokenResponse, dependencies=[Depends(_require_enabled), Depends(login_limit)])
def login(body: Credentials, db: Session = Depends(get_db)):
    """Exchange email + password for a token. Same message for unknown email and wrong password."""
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return TokenResponse(token=create_token(user.id), email=user.email)


# GET /api/v1/auth/me
# Example response: {"email": "vipul@example.com"}
@router.get("/me", dependencies=[Depends(_require_enabled)])
def me(request: Request, user_id=Depends(authenticate), db: Session = Depends(get_db)):
    """The signed-in user."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return {"email": user.email}
