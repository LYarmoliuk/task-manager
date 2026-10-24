"""Завдання 2-4 на рівні сервісів: повнота, мінімізація, видалення, згоди."""
import json

from app.privacy.services import (
    AccessDenied, Principal, PolicyGate, SubjectNotFound, anonymize_user,
    build_personal_data_export, grant_consent, revoke_consent,
    send_marketing_email, send_order_receipt,
)
from app.privacy.store import ALICE_PII, seed_demo_store

ALICE = Principal(1, "user")
BOB = Principal(2, "user")
ADMIN = Principal(3, "admin")
CID = "test-corr"


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return True
    raise AssertionError(f"expected {exc.__name__}")


# ----------------------------------------------------------------- експорт
def test_export_complete_for_own_data():
    store = seed_demo_store()
    data = build_personal_data_export(store, ALICE, 1, CID)
    assert data["meta"]["schema_version"] == "1.0"
    assert data["meta"]["timezone"] == "UTC" and data["meta"]["subject_id"] == 1
    assert data["profile"]["email"] == ALICE_PII["email"]
    assert data["settings"]["language"] == "uk"
    assert len(data["activity"]) == 2 and len(data["orders"]) == 1
    assert data["consents"] == []                  # передбачувана порожня структура
    json.dumps(data)                               # валідний JSON


def test_export_minimization_and_no_other_users():
    store = seed_demo_store()
    dump = json.dumps(build_personal_data_export(store, ALICE, 1, CID))
    assert ALICE_PII["hash"] not in dump and ALICE_PII["reset"] not in dump
    body = dump.split('"excluded_fields"')[0]      # поза документованим переліком пропусків
    for field_name in ("password_hash", "reset_token", "is_flagged_fraud"):
        assert f'"{field_name}"' not in body
    assert "bob@example.com" not in dump and "EXT-BOB-002" not in dump


def test_export_empty_categories_for_user_without_data():
    store = seed_demo_store()
    data = build_personal_data_export(store, ADMIN, 3, CID)
    assert data["activity"] == [] and data["orders"] == [] and data["settings"] == {}


def test_export_access_control():
    store = seed_demo_store()
    raises(AccessDenied, build_personal_data_export, store, BOB, 1, CID)
    assert build_personal_data_export(store, ADMIN, 1, CID)["meta"]["subject_id"] == 1
    raises(SubjectNotFound, build_personal_data_export, store, ADMIN, 999, CID)
    raises(AccessDenied, build_personal_data_export, store, BOB, 999, CID)  # без витоку існування


def test_export_audit_has_no_pii():
    store = seed_demo_store()
    build_personal_data_export(store, ALICE, 1, CID)
    assert store.audit and ALICE_PII["email"] not in repr(store.audit)


# ------------------------------------------------------------ анонімізація
def _pii_values():
    return list(ALICE_PII.values()) + ["203.0.113.10"]


def test_anonymize_removes_pii_keeps_business_records_and_integrity():
    store = seed_demo_store()
    assert any(v in repr(store.snapshot()) for v in _pii_values())
    result = anonymize_user(store, ALICE, 1, CID)
    assert result["status"] == "anonymized"
    state = repr(store.snapshot())
    for value in _pii_values():
        assert value not in state, f"PII survived: {value}"
    assert len([o for o in store.orders if o.user_id == 1]) == 1  # RETAIN
    assert store.orders[0].amount == 99.5 and store.orders[0].billing_name is None
    assert all(o.user_id in store.users for o in store.orders)    # FK цілісні
    assert all(e.user_id in store.users for e in store.activity)
    assert all(c.user_id in store.users for c in store.consents)
    assert store.users[2].email == "bob@example.com"              # чужі дані не чіпали
    assert "token-alice" not in store.tokens


def test_anonymize_is_idempotent():
    store = seed_demo_store()
    anonymize_user(store, ALICE, 1, CID)
    before = repr((store.users, store.settings, store.activity, store.orders))
    assert anonymize_user(store, ADMIN, 1, CID)["status"] == "already_anonymized"
    assert before == repr((store.users, store.settings, store.activity, store.orders))
    assert len(store.users) == 3                                   # нових профілів немає


def test_anonymize_forbidden_for_other_actor():
    store = seed_demo_store()
    raises(AccessDenied, anonymize_user, store, BOB, 1, CID)
    assert store.users[1].email == ALICE_PII["email"]


def test_anonymize_is_atomic_on_failure():
    store = seed_demo_store()

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    store.add_audit = boom               # збій в кінці транзакції
    raises(RuntimeError, anonymize_user, store, ALICE, 1, CID)
    assert store.users[1].email == ALICE_PII["email"]            # відкат
    assert store.users[1].anonymized_at is None
    assert 1 in store.settings and "token-alice" in store.tokens
    del store.add_audit                  # прибрати підміну
    assert anonymize_user(store, ALICE, 1, CID)["status"] == "anonymized"


def test_anonymized_emails_are_unique_and_not_reversible():
    store = seed_demo_store()
    anonymize_user(store, ALICE, 1, CID)
    anonymize_user(store, BOB, 2, CID)
    e1, e2 = store.users[1].email, store.users[2].email
    assert e1 != e2 and e1.endswith("@anon.local")
    assert "alice" not in e1 and "bob" not in e2


def test_audit_after_erasure_has_no_deleted_values():
    store = seed_demo_store()
    anonymize_user(store, ALICE, 1, CID)
    for value in _pii_values():
        assert value not in repr(store.audit)


# ------------------------------------------------------------------ згоди
def test_consent_scenario_deny_grant_allow_revoke_deny():
    store = seed_demo_store()
    gate = PolicyGate(store)
    assert gate.check(1, "MARKETING_EMAIL").reason == "NO_CONSENT"
    assert send_marketing_email(store, gate, 1, "autumn", CID)["sent"] is False
    assert store.outbox == []                                     # без побічного ефекту

    grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2026-10", "web", CID)
    assert gate.check(1, "MARKETING_EMAIL").allowed
    assert send_marketing_email(store, gate, 1, "autumn", CID)["sent"] is True
    assert len(store.outbox) == 1                                 # ефект є

    revoke_consent(store, ALICE, 1, "MARKETING_EMAIL", CID)
    after = send_marketing_email(store, gate, 1, "autumn", CID)
    assert after == {"sent": False, "decision": "DENY", "reason": "WITHDRAWN"}
    assert len(store.outbox) == 1                                 # нового ефекту немає


def test_consent_is_purpose_specific():
    store = seed_demo_store()
    gate = PolicyGate(store)
    grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2026-10", "web", CID)
    assert gate.check(1, "OPTIONAL_ANALYTICS").allowed is False
    assert gate.check(1, "UNKNOWN").reason == "UNKNOWN_PURPOSE"


def test_consent_idempotent_history_and_evidence():
    store = seed_demo_store()
    grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2026-10", "mobile_app", CID)
    assert grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2026-10", "mobile_app", CID)["changed"] is False
    revoke_consent(store, ALICE, 1, "MARKETING_EMAIL", CID)
    n = len(store.consents)
    assert revoke_consent(store, ALICE, 1, "MARKETING_EMAIL", CID)["changed"] is False
    assert len(store.consents) == n                               # повторний REVOKE без нових записів
    rec = store.consents[0]
    assert rec.policy_version == "2026-10" and rec.source == "mobile_app"
    assert rec.granted_at and rec.withdrawn_at and rec.updated_at
    grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2026-10", "web", CID)
    assert len(store.consents) == 2                               # історія, а не перезапис


def test_policy_version_mismatch_denied():
    store = seed_demo_store()
    gate = PolicyGate(store)
    grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2025-01", "web", CID)
    assert gate.check(1, "MARKETING_EMAIL").reason == "POLICY_VERSION_MISMATCH"


def test_consent_is_not_a_universal_flag():
    store = seed_demo_store()
    assert send_order_receipt(store, 1, 1)["sent"] is True        # без жодної згоди
    assert store.outbox[-1]["kind"] == "ORDER_RECEIPT"


def test_consent_requires_authorization():
    store = seed_demo_store()
    raises(AccessDenied, grant_consent, store, BOB, 1, "MARKETING_EMAIL", "2026-10", "web", CID)


def test_erasure_withdraws_active_consents():
    store = seed_demo_store()
    gate = PolicyGate(store)
    grant_consent(store, ALICE, 1, "MARKETING_EMAIL", "2026-10", "web", CID)
    anonymize_user(store, ALICE, 1, CID)
    assert gate.check(1, "MARKETING_EMAIL").reason == "WITHDRAWN"
