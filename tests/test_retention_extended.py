"""Нові бізнес-правила (додаються разом зі станом FAIL і мають лишитись зеленими у PASS)."""
import pytest

from app.privacy.retention import DEFAULT_RETENTION_DAYS, retention_days


@pytest.mark.parametrize("jurisdiction", ["UA", "EU", "US"])
@pytest.mark.parametrize("active", [True, False])
def test_support_and_backup_ignore_other_dimensions(jurisdiction, active):
    assert retention_days("support", jurisdiction, active) == 365
    assert retention_days("backup", jurisdiction, active) == 2555


@pytest.mark.parametrize("jurisdiction", ["UA", "EU", "US"])
def test_marketing_inactive_is_deleted_immediately(jurisdiction):
    assert retention_days("marketing", jurisdiction, False) == 0


@pytest.mark.parametrize("jurisdiction", ["UA", "EU", "US"])
def test_marketing_active_falls_back_to_default(jurisdiction):
    assert retention_days("marketing", jurisdiction, True) == DEFAULT_RETENTION_DAYS
