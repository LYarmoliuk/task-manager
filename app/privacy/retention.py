"""Строки зберігання персональних даних (днів): таблиці пошуку замість розгалужень."""

DEFAULT_RETENTION_DAYS = 180

# Найточніший ключ: (категорія, юрисдикція, активність)
_BY_FULL_KEY = {
    ("order", "UA", True): 1095,
    ("order", "UA", False): 1095,
    ("order", "EU", True): 2190,
    ("order", "EU", False): 2190,
    ("log", "EU", True): 90,
    ("profile", "EU", True): 30,
    ("profile", "EU", False): 30,
}

# Середній ключ: (категорія, активність)
_BY_CATEGORY_ACTIVE = {
    ("consent", True): 3650,
    ("consent", False): 365,
    ("profile", False): 30,
    ("profile", True): 1095,
    ("marketing", False): 0,
}

# Правило для всієї категорії
_BY_CATEGORY = {
    "order": 1825,
    "log": 30,
    "support": 365,
    "backup": 2555,
}


def retention_days(category: str, jurisdiction: str, is_active: bool) -> int:
    return _BY_FULL_KEY.get(
        (category, jurisdiction, is_active),
        _BY_CATEGORY_ACTIVE.get((category, is_active), _BY_CATEGORY.get(category, DEFAULT_RETENTION_DAYS)),
    )
