import pytest

from auto_healer.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitBreakerPolicy,
    RetryPolicy,
    call_with_retry,
)


def test_call_with_retry_retries_until_success():
    attempts = {"count": 0}
    sleeps = []

    def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    result = call_with_retry(
        flaky_operation,
        retry_policy=RetryPolicy(enabled=True, max_attempts=3, backoff_seconds=2),
        sleep=sleeps.append,
    )

    assert result == "ok"
    assert attempts["count"] == 3
    assert sleeps == [2, 2]


def test_circuit_breaker_opens_after_failure_threshold():
    breaker = CircuitBreaker(
        CircuitBreakerPolicy(
            enabled=True,
            failure_threshold=2,
            reset_timeout_seconds=60,
        )
    )

    def failing_operation():
        raise RuntimeError("endpoint down")

    with pytest.raises(RuntimeError):
        breaker.call(failing_operation)
    with pytest.raises(RuntimeError):
        breaker.call(failing_operation)
    with pytest.raises(CircuitBreakerOpenError):
        breaker.call(lambda: "ok")
