"""Pulse CRM backend API.

Users, organizations and browser sessions are stored in PostgreSQL. The
database URL is configurable through ``DATABASE_URL``; a SQLite URL remains
useful for local smoke tests. Tables are created and the demo account is
seeded when the service starts. A migration tool can be introduced later
without changing the HTTP contract.
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import AuthSession, Organization, User
from .security import hash_password, new_session_token, session_token_hash, verify_password


APP_NAME = "Pulse CRM API"
SESSION_COOKIE = os.getenv("SESSION_COOKIE", "pulse_session")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@pulse.crm").strip().lower()
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}


def _cors_origins() -> list[str]:
    configured = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite's naive datetime values to timezone-aware UTC."""

    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _organization_payload(organization: Organization) -> dict[str, str]:
    return {"id": organization.id, "name": organization.name, "slug": organization.slug}


def _user_payload(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "avatar": user.avatar,
        "organizations": [
            _organization_payload(organization)
            for organization in sorted(user.organizations, key=lambda item: item.name.lower())
        ],
    }


def _seed_demo_data(db: Session) -> None:
    """Create a demo account and attach it to two organizations.

    Seeding is idempotent: existing users and organizations are preserved and
    only missing associations are added. This makes container restarts safe.
    """

    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        password_hash, password_salt = hash_password(DEMO_PASSWORD)
        user = User(
            id="demo-user",
            email=DEMO_EMAIL,
            name="Алексей Смирнов",
            role="Руководитель продаж",
            avatar="АС",
            password_hash=password_hash,
            password_salt=password_salt,
        )
        db.add(user)
        db.flush()

    seed_organizations = (
        ("demo-pulse", "Pulse Demo"),
        ("demo-north", "Северный регион"),
    )
    for slug, name in seed_organizations:
        organization = db.scalar(select(Organization).where(Organization.slug == slug))
        if organization is None:
            organization = Organization(id=slug, name=name, slug=slug)
            db.add(organization)
            db.flush()
        if organization not in user.organizations:
            user.organizations.append(organization)

    db.commit()


def init_database() -> None:
    """Create tables and seed data, retrying while PostgreSQL starts."""

    retries = max(1, int(os.getenv("DB_INIT_RETRIES", "30")))
    delay_seconds = max(0.1, float(os.getenv("DB_INIT_RETRY_DELAY", "1")))
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
            with SessionLocal() as db:
                _seed_demo_data(db)
            return
        except SQLAlchemyError as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(delay_seconds)
    raise RuntimeError("Database initialization failed") from last_error


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    yield


app = FastAPI(title=APP_NAME, version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


def _current_user(session_id: str | None, db: Session) -> User:
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    auth_session = db.get(AuthSession, session_token_hash(session_id))
    if auth_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    if _as_utc(auth_session.expires_at) <= _utc_now():
        db.delete(auth_session)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = db.get(User, auth_session.user_id)
    if user is None:
        db.delete(auth_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": APP_NAME, "status": "ok", "docs": "/docs"}


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", tags=["auth"])
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash, user.password_salt):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    token = new_session_token()
    auth_session = AuthSession(
        token_hash=session_token_hash(token),
        user_id=user.id,
        expires_at=_utc_now() + timedelta(seconds=SESSION_TTL_SECONDS),
    )
    db.add(auth_session)
    # Avoid retaining expired rows indefinitely during normal login traffic.
    db.execute(delete(AuthSession).where(AuthSession.expires_at < _utc_now()))
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"user": _user_payload(user)}


@app.get("/api/auth/me", tags=["auth"])
def me(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return {"user": _user_payload(_current_user(session_id, db))}


@app.post("/api/auth/logout", tags=["auth"])
def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if session_id:
        auth_session = db.get(AuthSession, session_token_hash(session_id))
        if auth_session is not None:
            db.delete(auth_session)
            db.commit()
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@app.get("/api/organizations", tags=["organizations"])
def organizations(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _current_user(session_id, db)
    return {"organizations": [_organization_payload(item) for item in user.organizations]}


METRICS = {
    "revenue": {"value": "₽ 1,28 млн", "trend": "18,4% к прошлому месяцу"},
    "clients": {"value": "+48", "trend": "12,5% к прошлому месяцу"},
    "deals": {"value": "126", "note": "на ₽ 3,6 млн"},
    "tasks": {"value": "17", "note": "5 с высоким приоритетом"},
}

DEALS = [
    {"id": "deal-1001", "client": "ООО «Север»", "description": "Обновление лицензий", "amount": "₽ 420 000", "stage": "Переговоры", "owner": "Мария Волкова", "tone": "green"},
    {"id": "deal-1002", "client": "Ривер Банк", "description": "Корпоративный пакет", "amount": "₽ 280 000", "stage": "Коммерческое", "owner": "Алексей Петров", "tone": "blue"},
    {"id": "deal-1003", "client": "Студия «Точка»", "description": "Поддержка продукта", "amount": "₽ 95 000", "stage": "Закрытие", "owner": "Ирина Смирнова", "tone": "purple"},
]

ACTIVITY = [
    {"id": "activity-1", "type": "deal", "text": "Сделка с ООО Вектор переведена на этап «Переговоры»", "time": "10 минут назад"},
    {"id": "activity-2", "type": "call", "text": "Запланирован звонок с Марией Кузнецовой", "time": "1 час назад"},
    {"id": "activity-3", "type": "note", "text": "Добавлена заметка к сделке «ТехноПром»", "time": "Вчера"},
]


@app.get("/api/dashboard", tags=["dashboard"])
def dashboard(
    session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = _current_user(session_id, db)
    return {
        "user": _user_payload(user),
        "metrics": METRICS,
        "deals": DEALS,
        "activity": ACTIVITY,
        "generated_at": _utc_now().isoformat(),
    }


if __name__ == "__main__":  # pragma: no cover - convenience for local development
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)

