"""Модель даних і in-memory сховище (PII inventory реалізовано тут)."""
from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    id: int
    email: str
    full_name: str
    phone: str | None
    address: str | None
    external_id: str | None
    password_hash: str          # НІКОЛИ не експортується
    reset_token: str | None     # НІКОЛИ не експортується
    is_flagged_fraud: bool      # внутрішній antifraud-прапорець, не експортується
    role: str                   # "user" | "admin"
    created_at: datetime
    anonymized_at: datetime | None = None


@dataclass
class UserSettings:
    user_id: int
    language: str
    timezone: str
    theme: str


@dataclass
class ActivityEvent:
    id: int
    user_id: int
    action: str
    ip_address: str | None
    user_agent: str | None
    occurred_at: datetime
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Order:
    id: int
    user_id: int
    amount: float
    currency: str
    status: str
    created_at: datetime
    billing_name: str | None
    billing_address: str | None


@dataclass
class ConsentRecord:
    id: int
    user_id: int
    purpose: str
    status: str                 # GRANTED | WITHDRAWN | SUPERSEDED
    policy_version: str
    source: str
    granted_at: datetime
    withdrawn_at: datetime | None
    updated_at: datetime


@dataclass
class AuditEvent:
    id: int
    timestamp: datetime
    action: str
    actor_id: int | None
    subject_id: int | None
    result: str
    correlation_id: str         # жодних значень PII


class PrivacyStore:
    _STATE = ("users", "settings", "activity", "orders", "consents",
              "audit", "tokens", "outbox")

    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.settings: dict[int, UserSettings] = {}
        self.activity: list[ActivityEvent] = []
        self.orders: list[Order] = []
        self.consents: list[ConsentRecord] = []
        self.audit: list[AuditEvent] = []
        self.tokens: dict[str, int] = {}
        self.outbox: list[dict[str, Any]] = []
        self._ids = itertools.count(1000)

    def next_id(self) -> int:
        return next(self._ids)

    def add_audit(self, action: str, actor_id: int | None,
                  subject_id: int | None, result: str, correlation_id: str) -> None:
        self.audit.append(AuditEvent(self.next_id(), utcnow(), action,
                                     actor_id, subject_id, result, correlation_id))

    # Транзакційна межа: знімок + відкат
    def snapshot(self) -> dict[str, Any]:
        return {n: copy.deepcopy(getattr(self, n)) for n in self._STATE}

    def restore(self, snap: dict[str, Any]) -> None:
        for name, value in snap.items():
            setattr(self, name, value)


# Контрольні тестові дані (синтетичні)
ALICE_PII = {
    "email": "alice@example.com", "name": "Alice Tester", "phone": "+380501234567",
    "address": "Kyiv, Test St 1", "external_id": "EXT-ALICE-001",
    "hash": "pbkdf2$ALICE_HASH_DO_NOT_EXPORT", "reset": "RESET-ALICE-TOKEN",
}


_DEMO_USER_AGENT = "Mozilla/5.0"


def seed_demo_store() -> PrivacyStore:
    s = PrivacyStore()
    now = utcnow()
    s.users[1] = User(1, ALICE_PII["email"], ALICE_PII["name"], ALICE_PII["phone"],
                      ALICE_PII["address"], ALICE_PII["external_id"], ALICE_PII["hash"],
                      ALICE_PII["reset"], True, "user", now)
    s.users[2] = User(2, "bob@example.com", "Bob Tester", "+380671112233",
                      "Lviv, Test St 2", "EXT-BOB-002", "pbkdf2$BOB_HASH",
                      "RESET-BOB-TOKEN", False, "user", now)
    s.users[3] = User(3, "admin@example.com", "Admin Tester", None, None, None,
                      "pbkdf2$ADMIN_HASH", None, False, "admin", now)
    s.settings[1] = UserSettings(1, "uk", "Europe/Kyiv", "dark")
    s.settings[2] = UserSettings(2, "en", "Europe/London", "light")
    s.activity += [
        ActivityEvent(1, 1, "LOGIN", "203.0.113.10", _DEMO_USER_AGENT, now,
                      {"note": "contact me at alice@example.com"}),
        ActivityEvent(2, 1, "TASK_CREATED", "203.0.113.10", _DEMO_USER_AGENT, now, {}),
        ActivityEvent(3, 2, "LOGIN", "198.51.100.7", _DEMO_USER_AGENT, now, {}),
    ]
    s.orders += [
        Order(1, 1, 99.5, "UAH", "PAID", now, "Alice Tester", "Kyiv, Test St 1"),
        Order(2, 2, 10.0, "UAH", "PAID", now, "Bob Tester", "Lviv, Test St 2"),
    ]
    s.tokens = {"token-alice": 1, "token-bob": 2, "token-admin": 3}
    return s
