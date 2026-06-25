from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, TypeVar


T = TypeVar("T")


class CircuitBreakerOpenError(RuntimeError):
    pass


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True)
class RetryPolicy:
    enabled: bool = True
    max_attempts: int = 3
    backoff_seconds: int = 2


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    enabled: bool = True
    failure_threshold: int = 5
    reset_timeout_seconds: int = 60


class CircuitBreaker:
    def __init__(
        self,
        policy: CircuitBreakerPolicy,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.policy = policy
        self._monotonic = monotonic
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if (
            self._state == CircuitState.OPEN
            and self._opened_at is not None
            and self._monotonic() - self._opened_at >= self.policy.reset_timeout_seconds
        ):
            return CircuitState.HALF_OPEN
        return self._state

    def call(self, operation: Callable[[], T]) -> T:
        if not self.policy.enabled:
            return operation()

        if self.state == CircuitState.OPEN:
            raise CircuitBreakerOpenError("circuit breaker is open")

        try:
            result = operation()
        except Exception:
            self._record_failure()
            raise

        self._record_success()
        return result

    def _record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.policy.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = self._monotonic()

    def _record_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None


def call_with_retry(
    operation: Callable[[], T],
    *,
    retry_policy: RetryPolicy,
    circuit_breaker: CircuitBreaker | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    attempts = retry_policy.max_attempts if retry_policy.enabled else 0
    total_attempts = attempts + 1
    last_error: Exception | None = None

    for attempt in range(total_attempts):
        try:
            if circuit_breaker is None:
                return operation()
            return circuit_breaker.call(operation)
        except CircuitBreakerOpenError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == total_attempts - 1:
                break
            if retry_policy.backoff_seconds > 0:
                sleep(retry_policy.backoff_seconds)

    if last_error is None:
        raise RuntimeError("operation failed without an exception")
    raise last_error
