"""HTTP-шар (FastAPI) для privacy-функцій. Підключення: install_privacy(app)."""
from __future__ import annotations

import logging
import re
import uuid

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.privacy.logging_security import configure_secure_logging, correlation_id_var
from app.privacy.services import (
    ROLE_ADMIN, AccessDenied, CURRENT_POLICY_VERSION, InvalidConsentPurpose,
    PolicyGate, Principal, SubjectErased, SubjectNotFound, anonymize_user,
    build_personal_data_export, grant_consent, revoke_consent, send_marketing_email,
)
from app.privacy.store import PrivacyStore, seed_demo_store

logger = logging.getLogger("app.privacy.http")
router = APIRouter()
_store = seed_demo_store()
_CID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def get_store() -> PrivacyStore:
    return _store


def get_principal(authorization: str | None = Header(default=None),
                  store: PrivacyStore = Depends(get_store)) -> Principal:
    """Імітація автентифікації: Bearer-токен -> (user_id, role)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
    user_id = store.tokens.get(authorization.removeprefix("Bearer ").strip())
    user = store.users.get(user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
    return Principal(user.id, user.role)


def cid() -> str:
    return correlation_id_var.get()


class ConsentCommand(BaseModel):
    policy_version: str = CURRENT_POLICY_VERSION
    source: str = "api"


class MarketingCommand(BaseModel):
    campaign: str


@router.get("/api/users/{user_id}/personal-data")
def personal_data(user_id: int, principal: Principal = Depends(get_principal),
                  store: PrivacyStore = Depends(get_store)):
    return build_personal_data_export(store, principal, user_id, cid())


@router.post("/api/users/{user_id}/anonymize")
def anonymize(user_id: int, principal: Principal = Depends(get_principal),
              store: PrivacyStore = Depends(get_store)):
    return anonymize_user(store, principal, user_id, cid())


@router.post("/api/users/{user_id}/consents/{purpose}/grant")
def consent_grant(user_id: int, purpose: str, cmd: ConsentCommand,
                  principal: Principal = Depends(get_principal),
                  store: PrivacyStore = Depends(get_store)):
    return grant_consent(store, principal, user_id, purpose,
                         cmd.policy_version, cmd.source, cid())


@router.post("/api/users/{user_id}/consents/{purpose}/revoke")
def consent_revoke(user_id: int, purpose: str,
                   principal: Principal = Depends(get_principal),
                   store: PrivacyStore = Depends(get_store)):
    return revoke_consent(store, principal, user_id, purpose, cid())


@router.post("/api/marketing/send/{user_id}")
def marketing_send(user_id: int, cmd: MarketingCommand,
                   principal: Principal = Depends(get_principal),
                   store: PrivacyStore = Depends(get_store)):
    if principal.role != ROLE_ADMIN:
        raise AccessDenied()
    return send_marketing_email(store, PolicyGate(store), user_id, cmd.campaign, cid())


def install_privacy(app: FastAPI) -> None:
    configure_secure_logging()
    app.include_router(router)

    def _handler(status: int, detail: str):
        def handle(request: Request, exc: Exception):
            return JSONResponse(status_code=status, content={"detail": detail})
        return handle

    app.add_exception_handler(AccessDenied, _handler(403, "Access denied"))
    app.add_exception_handler(SubjectNotFound, _handler(404, "Subject not found"))
    app.add_exception_handler(InvalidConsentPurpose, _handler(422, "Unknown consent purpose"))
    app.add_exception_handler(SubjectErased, _handler(409, "Subject already erased"))

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        incoming = request.headers.get("x-correlation-id", "")
        correlation = incoming if _CID_RE.match(incoming) else uuid.uuid4().hex
        token = correlation_id_var.set(correlation)
        try:
            response = await call_next(request)
            # Не логуємо body/headers/query: лише метод, шлях, статус
            logger.info("request method=%s path=%s status=%s",
                        request.method, request.url.path, response.status_code)
        finally:
            correlation_id_var.reset(token)
        response.headers["X-Correlation-ID"] = correlation
        return response
