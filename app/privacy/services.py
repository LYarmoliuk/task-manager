"""Бізнес-логіка privacy: експорт, анонімізація, згоди, Policy Gate.
Без залежностей від FastAPI: легко тестується й переноситься."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.privacy.logging_security import safe_ref
from app.privacy.store import ConsentRecord, PrivacyStore, utcnow

logger = logging.getLogger("app.privacy")

ROLE_ADMIN = "admin"
EXPORT_SCHEMA_VERSION = "1.0"
CURRENT_POLICY_VERSION = "2026-10"
CONSENT_PURPOSES = frozenset({"MARKETING_EMAIL", "OPTIONAL_ANALYTICS"})

# Мінімізація: ці поля НІКОЛИ не потрапляють в експорт (documented omission)
EXCLUDED_FROM_EXPORT = {
    # Field NAMES that must never be exported (a deny-list, not credentials).
    "password_hash": "security-sensitive",  # NOSONAR
    "reset_token": "security-sensitive",
    "is_flagged_fraud": "internal antifraud flag",
    "auth_tokens": "integration/session secrets",
    "audit_log": "internal security records, not user data",
    "other_users_data": "data of other subjects",
}

# Політика обробки сутностей при праві на видалення
ERASURE_POLICY = {
    "users":       ("ANONYMIZE", "email/name/phone/address/external_id замінюються; password_hash і reset_token очищаються"),
    "settings":    ("DELETE",    "налаштування не потрібні після видалення суб'єкта"),
    "activity":    ("ANONYMIZE", "лишається подія й час (безпека/аналітика); ip, user_agent, meta очищаються"),
    "orders":      ("RETAIN",    "retention rule: бухгалтерський облік; billing_name/billing_address видаляються, лишаються сума, валюта, статус, дата"),
    "consents":    ("RETAIN",    "доказ дати/версії політики; PII немає; активні згоди відкликаються"),
    "audit":       ("RETAIN",    "privacy-safe: лише факт, час, actor, результат, correlation ID"),
    "auth_tokens": ("DELETE",    "сесії/токени суб'єкта анулюються"),
}


class AccessDenied(Exception): ...
class SubjectNotFound(Exception): ...
class InvalidConsentPurpose(Exception): ...
class SubjectErased(Exception): ...


@dataclass(frozen=True)
class Principal:
    user_id: int
    role: str


def _iso(dt: datetime | None) -> str | None:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def authorize_subject_access(store: PrivacyStore, principal: Principal,
                             subject_id: int, action: str, correlation_id: str) -> None:
    """Порівнюємо authenticated principal з subject ID, а не довіряємо path."""
    if principal.user_id == subject_id or principal.role == ROLE_ADMIN:
        return
    store.add_audit(action, principal.user_id, subject_id, "DENIED", correlation_id)
    logger.warning("%s denied actor=%s subject=%s", action,
                   safe_ref(principal.user_id), safe_ref(subject_id))
    raise AccessDenied()


# ---------------------------------------------------------------- Завдання 2
def build_personal_data_export(store: PrivacyStore, principal: Principal,
                               subject_id: int, correlation_id: str) -> dict:
    authorize_subject_access(store, principal, subject_id,
                             "PERSONAL_DATA_EXPORT", correlation_id)
    user = store.users.get(subject_id)
    if user is None:
        store.add_audit("PERSONAL_DATA_EXPORT", principal.user_id, subject_id,
                        "NOT_FOUND", correlation_id)
        raise SubjectNotFound()

    settings = store.settings.get(subject_id)
    export = {
        "meta": {
            "schema_version": EXPORT_SCHEMA_VERSION,
            "generated_at": _iso(utcnow()),
            "timezone": "UTC",
            "subject_id": subject_id,
            "requested_by": principal.user_id,
            "correlation_id": correlation_id,
            "categories": ["profile", "settings", "activity", "orders", "consents"],
            "excluded_fields": EXCLUDED_FROM_EXPORT,
        },
        "profile": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "phone": user.phone, "address": user.address,
            "external_id": user.external_id,
            "created_at": _iso(user.created_at),
            "anonymized": user.anonymized_at is not None,
        },
        "settings": ({"language": settings.language, "timezone": settings.timezone,
                      "theme": settings.theme} if settings else {}),
        "activity": [
            {"id": e.id, "action": e.action, "ip_address": e.ip_address,
             "user_agent": e.user_agent, "occurred_at": _iso(e.occurred_at),
             "meta": dict(e.meta)}
            for e in store.activity if e.user_id == subject_id
        ],
        "orders": [
            {"id": o.id, "amount": o.amount, "currency": o.currency,
             "status": o.status, "created_at": _iso(o.created_at),
             "billing_name": o.billing_name, "billing_address": o.billing_address}
            for o in store.orders if o.user_id == subject_id
        ],
        "consents": [consent_view(c) for c in store.consents if c.user_id == subject_id],
    }
    store.add_audit("PERSONAL_DATA_EXPORT", principal.user_id, subject_id,
                    "SUCCESS", correlation_id)
    # Лог: лише факт, безпечні ідентифікатори, результат. Без JSON експорту.
    logger.info("personal_data_export actor=%s subject=%s result=SUCCESS",
                safe_ref(principal.user_id), safe_ref(subject_id))
    return export


# ---------------------------------------------------------------- Завдання 3
def anonymize_user(store: PrivacyStore, principal: Principal,
                   subject_id: int, correlation_id: str) -> dict:
    authorize_subject_access(store, principal, subject_id, "ANONYMIZE", correlation_id)
    user = store.users.get(subject_id)
    if user is None:
        store.add_audit("ANONYMIZE", principal.user_id, subject_id,
                        "NOT_FOUND", correlation_id)
        raise SubjectNotFound()
    if user.anonymized_at is not None:  # ідемпотентність
        store.add_audit("ANONYMIZE", principal.user_id, subject_id,
                        "NOOP_ALREADY_ANONYMIZED", correlation_id)
        return {"status": "already_anonymized", "subject_id": subject_id}

    snapshot = store.snapshot()  # початок транзакції
    try:
        now = utcnow()
        # Унікальне, не відновлюване значення (не залежить від початкових даних)
        user.email = f"deleted-{subject_id}@anon.local"
        user.full_name = "Anonymized User"
        user.phone = None
        user.address = None
        user.external_id = None
        user.password_hash = ""
        user.reset_token = None
        user.is_flagged_fraud = False
        user.anonymized_at = now

        store.settings.pop(subject_id, None)                      # DELETE
        for ev in store.activity:                                 # ANONYMIZE
            if ev.user_id == subject_id:
                ev.ip_address, ev.user_agent, ev.meta = None, None, {}
        for order in store.orders:                                # RETAIN, без PII
            if order.user_id == subject_id:
                order.billing_name, order.billing_address = None, None
        for c in store.consents:                                  # RETAIN + відкликання
            if c.user_id == subject_id and c.status == "GRANTED":
                c.status, c.withdrawn_at, c.updated_at = "WITHDRAWN", now, now
        store.tokens = {t: u for t, u in store.tokens.items() if u != subject_id}

        store.add_audit("ANONYMIZE", principal.user_id, subject_id,
                        "SUCCESS", correlation_id)               # без значень PII
    except Exception:
        store.restore(snapshot)                                   # відкат
        logger.error("anonymize failed and rolled back subject=%s", safe_ref(subject_id))
        raise
    logger.info("anonymize actor=%s subject=%s result=SUCCESS",
                safe_ref(principal.user_id), safe_ref(subject_id))
    return {"status": "anonymized", "subject_id": subject_id,
            "policy": {k: v[0] for k, v in ERASURE_POLICY.items()}}


# ---------------------------------------------------------------- Завдання 4
def consent_view(c: ConsentRecord) -> dict:
    return {"id": c.id, "purpose": c.purpose, "status": c.status,
            "policy_version": c.policy_version, "source": c.source,
            "granted_at": _iso(c.granted_at), "withdrawn_at": _iso(c.withdrawn_at),
            "updated_at": _iso(c.updated_at)}


def _latest(store: PrivacyStore, subject_id: int, purpose: str) -> ConsentRecord | None:
    records = [c for c in store.consents
               if c.user_id == subject_id and c.purpose == purpose]
    return records[-1] if records else None


def _validate(store: PrivacyStore, subject_id: int, purpose: str) -> None:
    if purpose not in CONSENT_PURPOSES:
        raise InvalidConsentPurpose(purpose)
    user = store.users.get(subject_id)
    if user is None:
        raise SubjectNotFound()
    if user.anonymized_at is not None:
        raise SubjectErased()


def grant_consent(store: PrivacyStore, principal: Principal, subject_id: int,
                  purpose: str, policy_version: str, source: str,
                  correlation_id: str) -> dict:
    authorize_subject_access(store, principal, subject_id, "CONSENT_GRANT", correlation_id)
    _validate(store, subject_id, purpose)
    now = utcnow()
    latest = _latest(store, subject_id, purpose)
    if latest and latest.status == "GRANTED":
        if latest.policy_version == policy_version:  # ідемпотентно
            return {"changed": False, "consent": consent_view(latest)}
        latest.status, latest.updated_at = "SUPERSEDED", now
    record = ConsentRecord(store.next_id(), subject_id, purpose, "GRANTED",
                           policy_version, source, now, None, now)
    store.consents.append(record)  # історія зберігається, а не перезаписується
    store.add_audit("CONSENT_GRANT", principal.user_id, subject_id, "SUCCESS", correlation_id)
    logger.info("consent_grant purpose=%s subject=%s", purpose, safe_ref(subject_id))
    return {"changed": True, "consent": consent_view(record)}


def revoke_consent(store: PrivacyStore, principal: Principal, subject_id: int,
                   purpose: str, correlation_id: str) -> dict:
    authorize_subject_access(store, principal, subject_id, "CONSENT_REVOKE", correlation_id)
    _validate(store, subject_id, purpose)
    latest = _latest(store, subject_id, purpose)
    if latest is None or latest.status != "GRANTED":  # ідемпотентно
        store.add_audit("CONSENT_REVOKE", principal.user_id, subject_id,
                        "NOOP", correlation_id)
        return {"changed": False, "status": latest.status if latest else "NONE"}
    now = utcnow()
    latest.status, latest.withdrawn_at, latest.updated_at = "WITHDRAWN", now, now
    store.add_audit("CONSENT_REVOKE", principal.user_id, subject_id, "SUCCESS", correlation_id)
    logger.info("consent_revoke purpose=%s subject=%s", purpose, safe_ref(subject_id))
    return {"changed": True, "consent": consent_view(latest)}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


class PolicyGate:
    """Читає актуальний стан з сховища при КОЖНОМУ виклику (без кешу),
    тому відкликання діє негайно."""

    def __init__(self, store: PrivacyStore,
                 required_policy_version: str = CURRENT_POLICY_VERSION) -> None:
        self.store = store
        self.required_policy_version = required_policy_version

    def check(self, subject_id: int, purpose: str) -> Decision:
        if purpose not in CONSENT_PURPOSES:
            return Decision(False, "UNKNOWN_PURPOSE")
        latest = _latest(self.store, subject_id, purpose)
        if latest is None:
            return Decision(False, "NO_CONSENT")
        if latest.status == "WITHDRAWN":
            return Decision(False, "WITHDRAWN")
        if latest.status != "GRANTED":
            return Decision(False, "NO_CONSENT")
        if latest.policy_version != self.required_policy_version:
            return Decision(False, "POLICY_VERSION_MISMATCH")
        return Decision(True, "ALLOW")


def send_marketing_email(store: PrivacyStore, gate: PolicyGate, subject_id: int,
                         campaign: str, correlation_id: str) -> dict:
    """Залежна дія: перевірка згоди безпосередньо ПЕРЕД побічним ефектом."""
    decision = gate.check(subject_id, "MARKETING_EMAIL")
    if not decision.allowed:
        store.add_audit("MARKETING_SEND", None, subject_id,
                        f"DENY:{decision.reason}", correlation_id)
        return {"sent": False, "decision": "DENY", "reason": decision.reason}
    store.outbox.append({"kind": "MARKETING_EMAIL", "user_id": subject_id,
                         "campaign": campaign})
    store.add_audit("MARKETING_SEND", None, subject_id, "ALLOW", correlation_id)
    return {"sent": True, "decision": "ALLOW", "reason": "ALLOW"}


def send_order_receipt(store: PrivacyStore, subject_id: int, order_id: int) -> dict:
    """Договірна/системна функція: НЕ залежить від marketing-згоди."""
    user = store.users.get(subject_id)
    if user is None or user.anonymized_at is not None:
        return {"sent": False, "reason": "SUBJECT_UNAVAILABLE"}
    store.outbox.append({"kind": "ORDER_RECEIPT", "user_id": subject_id,
                         "order_id": order_id})
    return {"sent": True, "reason": "CONTRACTUAL"}
