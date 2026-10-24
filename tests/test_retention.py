import pytest

from app.privacy.retention import DEFAULT_RETENTION_DAYS, retention_days


@pytest.mark.parametrize(
    "category, jurisdiction, active, expected",
    [
        ("order", "UA", True, 1095), ("order", "UA", False, 1095),
        ("order", "EU", True, 2190), ("order", "EU", False, 2190),
        ("order", "US", True, 1825), ("order", "US", False, 1825),
        ("log", "EU", True, 90), ("log", "EU", False, 30),
        ("log", "UA", True, 30), ("log", "US", False, 30),
        ("consent", "UA", True, 3650), ("consent", "EU", False, 365),
        ("profile", "UA", False, 30), ("profile", "EU", True, 30),
        ("profile", "EU", False, 30), ("profile", "UA", True, 1095),
        ("profile", "US", True, 1095),
        ("unknown", "UA", True, DEFAULT_RETENTION_DAYS),
    ],
)
def test_baseline_rules(category, jurisdiction, active, expected):
    assert retention_days(category, jurisdiction, active) == expected
