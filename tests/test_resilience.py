from unittest.mock import patch

from app.main import get_dependency_with_resilience


def test_dependency_success_without_fallback() -> None:
    fake_response = type(
        "FakeResponse",
        (),
        {
            "__enter__": lambda self: self,
            "__exit__": lambda self, exc_type, exc_value, traceback: None,
        },
    )()

    fake_response.status = 200

    with patch(
        "app.main.urllib.request.urlopen",
        return_value=fake_response,
    ) as mock_urlopen:
        result = get_dependency_with_resilience()

    assert result == {
        "status": "ok",
        "source": "external",
        "attempts": 1,
    }

    mock_urlopen.assert_called_once()


def test_dependency_failure_uses_fallback_after_three_attempts() -> None:
    with patch(
        "app.main.urllib.request.urlopen",
        side_effect=TimeoutError("simulated timeout"),
    ) as mock_urlopen:
        with patch("app.main.time.sleep"):
            result = get_dependency_with_resilience()

    assert result == {
        "status": "fallback",
        "source": "fallback",
        "attempts": 3,
    }

    assert mock_urlopen.call_count == 3