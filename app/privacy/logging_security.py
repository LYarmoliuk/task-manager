"""Централізоване безпечне логування (Завдання 1).

Єдина точка контролю: кожен LogRecord санітизується в момент створення
(Logger.makeRecord), тому захист діє для ВСІХ логерів і хендлерів,
а не лише для місць, де розробник не забув замаскувати вручну.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import logging
import re
import traceback
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

REDACTED = "[REDACTED]"

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)

# Ключі, значення яких ЗАВЖДИ повністю замінюються (політика: FORBIDDEN).
_SECRET_KEY_PARTS = (
    "password", "passwd", "token", "secret",
    "api_key", "apikey", "api-key", "authorization", "cookie",
)

_SECRET_WORDS = (
    "password_hash", "password", "passwd", "access_token", "refresh_token",
    "reset_token", "session_secret", r"api[_-]?key", "secret", "token", "authorization",
)
_SECRET_KV_RE = re.compile(
    r"""(?P<key>["']?(?:""" + "|".join(_SECRET_WORDS) + r""")["']?)"""
    r"""(?P<sep>\s*[:=]\s*)"""
    r"""(?P<val>"[^"]*"|'[^']*'|Bearer\s+[^\s,;"']+|[^\s,;)}\]&"']+)""",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"Bearer\s+[a-z0-9._~+/=-]+", re.IGNORECASE)
_TOKEN_LIKE_RE = re.compile(
    r"\b(?:ghp_[A-Za-z0-9]{20,}|sk_(?:live|test)_[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16})\b"
)
_EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]{1,254})@((?:[A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24})")
_PHONE_RE = re.compile(r"(?<![\w*])\+?\d[\d\s().-]{7,}\d(?!\w)")


def _redact_kv(match: re.Match[str]) -> str:
    val = match.group("val")
    if val[:1] in ("'", '"'):
        quote = val[0]
        redacted = f"{quote}{REDACTED}{quote}"
    else:
        redacted = REDACTED
    return f"{match.group('key')}{match.group('sep')}{redacted}"


def _mask_email(match: re.Match[str]) -> str:
    return f"{match.group(1)[0]}***@{match.group(2)}"  # MASKED: a***@domain


def _mask_phone(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) < 9:  # дати, лічильники тощо не чіпаємо
        return match.group(0)
    return "***" + digits[-2:]


def sanitize_text(text: str) -> str:
    text = _SECRET_KV_RE.sub(_redact_kv, text)
    text = _BEARER_RE.sub(f"Bearer {REDACTED}", text)
    text = _TOKEN_LIKE_RE.sub(REDACTED, text)
    text = _EMAIL_RE.sub(_mask_email, text)
    text = _PHONE_RE.sub(_mask_phone, text)
    return text


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def sanitize_obj(value: Any, key: str | None = None) -> Any:
    """Рекурсивна санітизація dict/list/dataclass/DTO/exception."""
    if key is not None and _is_secret_key(key):
        return REDACTED
    if isinstance(value, str):
        return sanitize_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, Mapping):
        return {str(k): sanitize_obj(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [sanitize_obj(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return sanitize_obj(asdict(value))
    if hasattr(value, "model_dump"):  # pydantic DTO
        return sanitize_obj(value.model_dump())
    if isinstance(value, BaseException):
        return sanitize_text(f"{type(value).__name__}: {value}")
    return sanitize_text(str(value))


_STANDARD_ATTRS = frozenset(
    logging.LogRecord("x", 0, "x", 0, "x", (), None).__dict__
) | {"message", "asctime", "exc_type", "correlation_id", "_sanitized"}


def sanitize_record(record: logging.LogRecord) -> logging.LogRecord:
    if getattr(record, "_sanitized", False):
        return record
    if record.name.startswith("uvicorn"):
        # Форматери uvicorn відновлюють рядок із record.args (client, method,
        # path, version, status) і color_message. Структуру args зберігаємо,
        # санітизуємо кожен елемент окремо (напр. token=... у query-рядку).
        record.msg = sanitize_text(str(record.msg))
        if isinstance(record.args, tuple):
            record.args = tuple(sanitize_obj(a) for a in record.args)
    else:
        try:
            message = record.getMessage()
        except Exception:  # некоректний формат не повинен ламати логування
            message = str(record.msg)
        record.msg = sanitize_text(message)
        record.args = ()

    if record.exc_info and record.exc_info[0] is not None:
        record.exc_type = record.exc_info[0].__name__  # діагностика збережена
        formatted = "".join(traceback.format_exception(*record.exc_info))
        record.exc_text = sanitize_text(formatted)
        record.exc_info = None
    elif record.exc_text:
        record.exc_text = sanitize_text(record.exc_text)

    for attr in record.__dict__:
        if attr not in _STANDARD_ATTRS and not attr.startswith("_"):
            record.__dict__[attr] = sanitize_obj(record.__dict__[attr], attr)

    if not hasattr(record, "correlation_id"):
        record.correlation_id = correlation_id_var.get()
    record._sanitized = True
    return record


class JsonFormatter(logging.Formatter):
    """Структурований JSON-лог; не втрачає correlation_id, level, logger."""

    def format(self, record: logging.LogRecord) -> str:
        sanitize_record(record)
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": record.correlation_id,
        }
        for attr, val in record.__dict__.items():
            if attr not in _STANDARD_ATTRS and not attr.startswith("_"):
                payload[attr] = val
        if getattr(record, "exc_type", None):
            payload["exc_type"] = record.exc_type
        if record.exc_text:
            payload["exception"] = record.exc_text
        return json.dumps(payload, ensure_ascii=False, default=str)


_original_make_record = logging.Logger.makeRecord
_installed = False


def install_log_sanitizer() -> None:
    """Єдина точка інтеграції: санітизація кожного LogRecord (ідемпотентно)."""
    global _installed
    if _installed:
        return

    def make_record(self, *args, **kwargs):  # noqa: ANN001
        return sanitize_record(_original_make_record(self, *args, **kwargs))

    logging.Logger.makeRecord = make_record  # type: ignore[assignment]
    _installed = True


def configure_secure_logging(level: int = logging.INFO) -> None:
    install_log_sanitizer()
    root = logging.getLogger()
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(level)


def safe_ref(value: object) -> str:
    """Безпечний ідентифікатор для логів: хеш-посилання замість значення."""
    return "ref_" + hashlib.sha256(str(value).encode()).hexdigest()[:8]