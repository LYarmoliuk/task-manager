"""Інтеграційні HTTP-тести (потребують fastapi + httpx, як і решта проєкту)."""
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.privacy.api import get_store, install_privacy
from app.privacy.store import ALICE_PII, seed_demo_store

ALICE = {"Authorization": "Bearer token-alice"}
BOB = {"Authorization": "Bearer token-bob"}
ADMIN = {"Authorization": "Bearer token-admin"}


@pytest.fixture
def env():
    store = seed_demo_store()
    app = FastAPI()
    install_privacy(app)
    app.dependency_overrides[get_store] = lambda: store
    return TestClient(app), store


def test_export_own_data(env):
    client, _ = env
    r = client.get("/api/users/1/personal-data", headers=ALICE)
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["schema_version"] == "1.0" and body["profile"]["email"] == ALICE_PII["email"]
    assert len(body["activity"]) == 2 and len(body["orders"]) == 1
    assert "password_hash" not in r.text.split('"excluded_fields"')[0]
    assert "X-Correlation-ID" in r.headers


def test_export_requires_authentication(env):
    client, _ = env
    assert client.get("/api/users/1/personal-data").status_code == 401
    assert client.get("/api/users/1/personal-data",
                      headers={"Authorization": "Bearer nope"}).status_code == 401


def test_export_foreign_user_denied_without_data(env):
    client, _ = env
    r = client.get("/api/users/1/personal-data", headers=BOB)
    assert r.status_code == 403
    assert r.json() == {"detail": "Access denied"}
    assert "alice" not in r.text.lower()


def test_export_nonexistent_subject(env):
    client, _ = env
    assert client.get("/api/users/999/personal-data", headers=ADMIN).status_code == 404
    assert client.get("/api/users/999/personal-data", headers=BOB).status_code == 403


def test_export_does_not_leak_pii_to_logs(env, caplog):
    client, _ = env
    caplog.set_level(logging.DEBUG)
    client.get("/api/users/1/personal-data", headers=ALICE)
    text = " ".join(r.getMessage() for r in caplog.records)
    for value in ALICE_PII.values():
        assert value not in text
    assert "Alice" not in text and "schema_version" not in text  # повний JSON не логується


def test_anonymize_flow_and_authorization(env):
    client, store = env
    assert client.get("/api/users/1/anonymize", headers=ALICE).status_code == 405
    assert client.post("/api/users/1/anonymize", headers=BOB).status_code == 403
    assert store.users[1].email == ALICE_PII["email"]
    r = client.post("/api/users/1/anonymize", headers=ALICE)
    assert r.status_code == 200 and r.json()["status"] == "anonymized"
    assert client.post("/api/users/1/anonymize", headers=ADMIN).json()["status"] == "already_anonymized"
    export = client.get("/api/users/1/personal-data", headers=ADMIN).json()
    assert export["profile"]["email"] == "deleted-1@anon.local"
    assert ALICE_PII["email"] not in repr(store.snapshot())


def test_consent_flow_over_http(env):
    client, store = env
    send = lambda: client.post("/api/marketing/send/1", json={"campaign": "c1"}, headers=ADMIN)
    assert send().json()["decision"] == "DENY" and store.outbox == []
    g = client.post("/api/users/1/consents/MARKETING_EMAIL/grant",
                    json={"policy_version": "2026-10", "source": "web"}, headers=ALICE)
    assert g.status_code == 200 and g.json()["changed"] is True
    assert send().json()["decision"] == "ALLOW" and len(store.outbox) == 1
    assert client.post("/api/users/1/consents/MARKETING_EMAIL/revoke", headers=ALICE).json()["changed"] is True
    assert send().json() == {"sent": False, "decision": "DENY", "reason": "WITHDRAWN"}
    assert len(store.outbox) == 1


def test_consent_validation_and_authorization(env):
    client, _ = env
    assert client.post("/api/users/1/consents/BOGUS/grant", json={}, headers=ALICE).status_code == 422
    assert client.post("/api/users/1/consents/MARKETING_EMAIL/grant", json={}, headers=BOB).status_code == 403
    assert client.post("/api/marketing/send/1", json={"campaign": "x"}, headers=ALICE).status_code == 403
