import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """DRF's ScopedRateThrottle tracks request counts in Django's cache,
    which otherwise persists across test functions in the same process and
    causes unrelated tests to fail with 429s once enough of them hit a
    throttled endpoint (e.g. /auth/login) in one test run.
    """
    cache.clear()
    yield
