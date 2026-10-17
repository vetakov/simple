"""Pulse CRM backend API.

The service intentionally keeps authentication in memory for the demo. Replace
``SESSION_STORE`` with a persistent session/token store before deploying to
multiple replicas or production.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import Cookie, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


APP_NAME = "Pulse CRM API"
SESSION_COOKIE = os.getenv("SESSION_COOKIE", "pulse_session")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@pulse.crm")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo123")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}


def _cors_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


app = FastAPI(title=APP_NAME, version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# token -> user object. This is intentionally process-local demo state.
SESSION_STORE: dict[str, dict[str, Any]] = {}


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class User(BaseModel):
    id: str
    name: str
    email: str
    role: str
    avatar: str | None = None


DEMO_USER = User(
    id="demo-user",
    name="Алексей Смирнов",
    email=DEMO_EMAIL,
    role="Руководитель продаж",
    avatar="АС",
)


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


def _user_payload(user: User) -> dict[str, Any]:
    return user.model_dump()


def _current_user(session_id: str | None) -> User:
    if not session_id or session_id not in SESSION_STORE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return User.model_validate(SESSION_STORE[session_id])


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": APP_NAME, "status": "ok", "docs": "/docs"}


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login", tags=["auth"])
def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    if payload.email.strip().lower() != DEMO_EMAIL.lower() or payload.password != DEMO_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    session_id = secrets.token_urlsafe(32)
    SESSION_STORE[session_id] = _user_payload(DEMO_USER)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return {"user": _user_payload(DEMO_USER)}


@app.get("/api/auth/me", tags=["auth"])
def me(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, Any]:
    user = _current_user(session_id)
    return {"user": _user_payload(user)}


@app.post("/api/auth/logout", tags=["auth"])
def logout(response: Response, session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, str]:
    if session_id:
        SESSION_STORE.pop(session_id, None)
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"status": "ok"}


@app.get("/api/dashboard", tags=["dashboard"])
def dashboard(session_id: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, Any]:
    user = _current_user(session_id)
    return {
        "user": _user_payload(user),
        "metrics": METRICS,
        "deals": DEALS,
        "activity": ACTIVITY,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":  # pragma: no cover - convenience for local development
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
