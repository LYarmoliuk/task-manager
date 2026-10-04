import logging
import time
import urllib.request


logger = logging.getLogger(__name__)

DEPENDENCY_URL = "http://127.0.0.1:9001/data"
MAX_ATTEMPTS = 3


def request_dependency() -> int:
    with urllib.request.urlopen(
        DEPENDENCY_URL,
        timeout=1,
    ) as response:
        return response.status


def get_fallback_response() -> dict[str, str | int]:
    return {
        "status": "fallback",
        "source": "fallback",
        "attempts": MAX_ATTEMPTS,
    }


def get_dependency_with_resilience() -> dict[str, str | int]:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            request_dependency()

            logger.info(
                "Dependency succeeded on attempt %s",
                attempt,
            )

            return {
                "status": "ok",
                "source": "external",
                "attempts": attempt,
            }

        except Exception as error:
            logger.warning(
                "Dependency attempt %s/%s failed: %s",
                attempt,
                MAX_ATTEMPTS,
                error,
            )

            if attempt < MAX_ATTEMPTS:
                time.sleep(0.1 * (2 ** (attempt - 1)))

    logger.error(
        "Dependency unavailable after %s attempts. Using fallback.",
        MAX_ATTEMPTS,
    )

    return get_fallback_response()