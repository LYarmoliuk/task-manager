"""Строки відповіді на запити суб'єктів даних (DSR), днів: таблиці пошуку."""

DEFAULT_DEADLINE_DAYS = 90

_BY_FULL_KEY = {
    ("access", "EU", True): 7,
    ("access", "EU", False): 30,
    ("access", "UA", True): 10,
    ("access", "UA", False): 30,
    ("erasure", "EU", True): 14,
    ("erasure", "EU", False): 30,
    ("erasure", "UA", True): 30,
    ("erasure", "UA", False): 30,
}

_BY_TYPE_URGENT = {
    ("rectification", True): 15,
}

_BY_TYPE = {
    "access": 45,
    "erasure": 60,
    "rectification": 30,
}


def dsr_deadline_days(request_type: str, region: str, is_urgent: bool) -> int:
    return _BY_FULL_KEY.get(
        (request_type, region, is_urgent),
        _BY_TYPE_URGENT.get((request_type, is_urgent), _BY_TYPE.get(request_type, DEFAULT_DEADLINE_DAYS)),
    )
