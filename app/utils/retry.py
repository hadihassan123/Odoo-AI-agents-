import logging
import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def retry_request(func: Callable[[], T], retries: int = 3, delay: float = 2.0) -> T:
    last_error = None
    for i in range(retries):
        try:
            return func()
        except Exception as e:  # noqa: BLE001
            last_error = e
            if i == retries - 1:
                logging.error("Failed after %s retries: %s", retries, str(e))
                raise
            time.sleep(delay)
            logging.warning("Retry %s failed: %s", i + 1, str(e))
    raise last_error  # pragma: no cover
