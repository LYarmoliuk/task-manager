import pytest

from app.privacy.dsr_deadline import dsr_deadline_days


@pytest.mark.parametrize(
    "request_type, region, urgent, expected",
    [
        ("access", "EU", True, 7), ("access", "EU", False, 30),
        ("access", "UA", True, 10), ("access", "UA", False, 30),
        ("access", "US", True, 45), ("access", "US", False, 45),
        ("erasure", "EU", True, 14), ("erasure", "EU", False, 30),
        ("erasure", "UA", True, 30), ("erasure", "UA", False, 30),
        ("erasure", "US", True, 60), ("erasure", "US", False, 60),
        ("rectification", "EU", True, 15), ("rectification", "UA", True, 15),
        ("rectification", "EU", False, 30), ("rectification", "US", False, 30),
        ("portability", "EU", True, 90), ("portability", "US", False, 90),
    ],
)
def test_deadlines(request_type, region, urgent, expected):
    assert dsr_deadline_days(request_type, region, urgent) == expected
