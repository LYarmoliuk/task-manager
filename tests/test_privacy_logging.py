"""Завдання 1: тести безпечного логування (позитивні й негативні)."""
import io
import json
import logging
import uuid
from dataclasses import dataclass

from app.privacy.logging_security import (
    JsonFormatter, correlation_id_var, install_log_sanitizer,
)

install_log_sanitizer()

EMAIL = "alice@example.com"
PHONE = "+380501234567"
PASSWORD = "S3cretPassw0rd!"
TOKEN = "tok_ACCESS_123456789"
API_KEY = "KEY_ABCDEF_987654"  # gitleaks:allow (синтетичне тестове значення)
SENSITIVE = [EMAIL, PHONE, "380501234567", PASSWORD, TOKEN, API_KEY]


def make_logger():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(f"test.secure.{uuid.uuid4().hex}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    return logger, stream


def assert_no_leak(output: str, values=SENSITIVE) -> None:
    """FAIL, якщо хоча б одне вихідне sensitive-значення потрапило до логу."""
    leaked = [v for v in values if v in output]
    assert not leaked, f"LEAK in log output: {leaked}"


@dataclass
class ProfileDTO:
    phone: str
    api_key: str


@dataclass
class UserDTO:
    email: str
    password: str
    profile: ProfileDTO


def test_plain_text_is_masked_and_diagnostics_kept():
    logger, stream = make_logger()
    token = correlation_id_var.set("corr-123")
    try:
        logger.info("login op=LOGIN email=%s phone=%s password=%s", EMAIL, PHONE, PASSWORD)
    finally:
        correlation_id_var.reset(token)
    out = stream.getvalue()
    assert_no_leak(out)
    record = json.loads(out)                       # формат лога не зруйновано
    assert "a***@example.com" in record["message"]  # часткове маскування email
    assert "op=LOGIN" in record["message"]          # тип операції збережено
    assert record["correlation_id"] == "corr-123"   # correlation ID збережено
    assert "password=[REDACTED]" in record["message"]


def test_structured_json_payload_nested():
    logger, stream = make_logger()
    logger.info("request", extra={"payload": {
        "email": EMAIL, "password": PASSWORD, "access_token": TOKEN,
        "nested": {"phone": PHONE, "api_key": API_KEY}, "items": [{"token": TOKEN}],
    }})
    out = stream.getvalue()
    assert_no_leak(out)
    payload = json.loads(out)["payload"]
    assert payload["password"] == "[REDACTED]"
    assert payload["access_token"] == "[REDACTED]"
    assert payload["nested"]["api_key"] == "[REDACTED]"
    assert payload["items"][0]["token"] == "[REDACTED]"


def test_exception_message_is_sanitized_but_type_kept():
    logger, stream = make_logger()
    try:
        raise ValueError(f"failed for {EMAIL} token={TOKEN} phone {PHONE}")
    except ValueError:
        logger.exception("operation failed")
    out = stream.getvalue()
    assert_no_leak(out)
    record = json.loads(out)
    assert record["exc_type"] == "ValueError"       # діагностична цінність
    assert "ValueError" in record["exception"]


def test_negative_nested_dto_in_message_and_extra():
    logger, stream = make_logger()
    dto = UserDTO(EMAIL, PASSWORD, ProfileDTO(PHONE, API_KEY))
    logger.info("created dto=%s", dto)                 # через repr
    logger.info("created", extra={"dto": dto})         # через вкладений об'єкт
    out = stream.getvalue()
    assert_no_leak(out)
    lines = [json.loads(line) for line in out.strip().splitlines()]
    assert lines[1]["dto"]["profile"]["api_key"] == "[REDACTED]"


def test_negative_exception_object_as_argument():
    logger, stream = make_logger()
    logger.warning("caught %s", ValueError(f"bad {EMAIL} password={PASSWORD}"))
    assert_no_leak(stream.getvalue())


def test_leak_checker_itself_fails_on_leak():
    """Мета-тест: перевірка справді падає, якщо секрет у виводі."""
    try:
        assert_no_leak(f"oops {EMAIL}")
    except AssertionError:
        return
    raise AssertionError("assert_no_leak must fail when a leak is present")


def test_uvicorn_style_structured_args_are_preserved_and_sanitized():
    """Регресія: uvicorn.access розпаковує record.args (5 значень).
    Санітайзер не повинен їх ламати, але має чистити секрети в path."""
    class UvicornLikeFormatter(logging.Formatter):
        def formatMessage(self, record):
            client, method, path, version, status = record.args
            return f"{client} {method} {path} {version} {status}"

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(UvicornLikeFormatter())
    logger = logging.getLogger(f"uvicorn.access.{uuid.uuid4().hex}")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:5000", "GET",
                "/x?token=ABC123SECRETVALUE", "1.1", 200)
    out = stream.getvalue()
    assert "200" in out and "GET" in out             # логування не зламано
    assert "ABC123SECRETVALUE" not in out            # секрет у query замасковано