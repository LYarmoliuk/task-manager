"""Строки зберігання персональних даних (днів) за категорією, юрисдикцією і активністю."""

DEFAULT_RETENTION_DAYS = 180


def retention_days(category: str, jurisdiction: str, is_active: bool) -> int:
    if category == "order":
        if jurisdiction == "UA":
            return 1095
        elif jurisdiction == "EU":
            return 2190
        return 1825
    elif category == "log":
        if is_active and jurisdiction == "EU":
            return 90
        return 30
    elif category == "consent":
        if is_active:
            return 3650
        return 365
    elif category == "profile":
        if not is_active or jurisdiction == "EU":
            return 30
        return 1095
    elif category == "support":
        return 365
    elif category == "marketing" and not is_active:
        return 0
    elif category == "backup":
        return 2555
    return DEFAULT_RETENTION_DAYS
