"""Expo push — see docs/01-SYSTEM-ARCHITECTURE.md §8.

Still a no-op (Phase 5's original scope note carries forward): sending via
Expo's push API through a Celery task, so latency-sensitive call sites
(attendance check-in) never block on a provider round-trip, needs a real
Expo project/push credentials to test against that this environment
doesn't have. `Device.push_token` (Phase 2) is already where a token
would be read from once this is wired for real.
"""


def send_push(*, user, title, message):
    return None
