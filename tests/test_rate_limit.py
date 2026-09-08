from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from medintelos.api.app import create_app
from medintelos.config import Settings
from medintelos.rate_limit import TokenBucketLimiter

API_KEY = "test-key-with-sufficient-length"


def test_allows_up_to_burst_then_blocks():
    limiter = TokenBucketLimiter(requests_per_minute=60, burst=3)
    results = [limiter.allow("client-a")[0] for _ in range(4)]
    assert results == [True, True, True, False]


def test_distinct_keys_have_independent_buckets():
    limiter = TokenBucketLimiter(requests_per_minute=60, burst=1)
    assert limiter.allow("client-a")[0] is True
    assert limiter.allow("client-b")[0] is True
    assert limiter.allow("client-a")[0] is False


def test_tokens_refill_over_time():
    limiter = TokenBucketLimiter(requests_per_minute=6000, burst=1)  # 100/sec
    assert limiter.allow("client-a")[0] is True
    assert limiter.allow("client-a")[0] is False
    time.sleep(0.02)  # comfortably more than 1/100s
    assert limiter.allow("client-a")[0] is True


def test_retry_after_is_positive_when_blocked():
    limiter = TokenBucketLimiter(requests_per_minute=60, burst=1)
    limiter.allow("client-a")
    allowed, retry_after = limiter.allow("client-a")
    assert allowed is False
    assert retry_after > 0


def test_rejects_non_positive_config():
    with pytest.raises(ValueError):
        TokenBucketLimiter(requests_per_minute=0, burst=1)
    with pytest.raises(ValueError):
        TokenBucketLimiter(requests_per_minute=10, burst=0)


def test_evict_stale_removes_old_buckets():
    limiter = TokenBucketLimiter(requests_per_minute=60, burst=1)
    limiter.allow("client-a")
    removed = limiter.evict_stale(older_than_seconds=-1)  # everything is "stale"
    assert removed == 1


def _client(**overrides) -> TestClient:
    settings = Settings(
        environment="test",
        api_key=API_KEY,
        fhir_base_url="http://testserver",
        **overrides,
    )
    return TestClient(create_app(settings))


def test_api_returns_429_once_burst_is_exhausted():
    with _client(rate_limit_requests_per_minute=60, rate_limit_burst=2) as api:
        headers = {"X-API-Key": API_KEY}
        first = api.get("/fhir/R5/Patient?_count=1", headers=headers)
        second = api.get("/fhir/R5/Patient?_count=1", headers=headers)
        third = api.get("/fhir/R5/Patient?_count=1", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Retry-After" in third.headers


def test_health_endpoint_is_never_rate_limited():
    with _client(rate_limit_requests_per_minute=60, rate_limit_burst=1) as api:
        responses = [api.get("/health") for _ in range(5)]
    assert all(response.status_code == 200 for response in responses)


def test_rate_limit_can_be_disabled():
    with _client(
        rate_limit_enabled=False, rate_limit_requests_per_minute=60, rate_limit_burst=1
    ) as api:
        headers = {"X-API-Key": API_KEY}
        responses = [
            api.get("/fhir/R5/Patient?_count=1", headers=headers) for _ in range(5)
        ]
    assert all(response.status_code == 200 for response in responses)
