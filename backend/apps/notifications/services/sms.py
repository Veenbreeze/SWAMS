"""SMS-ready interface — see docs/01-SYSTEM-ARCHITECTURE.md §8 and
docs/04-PROJECT-STRUCTURE.md. No gateway is wired in v1 (the brief leaves
the provider choice open — e.g. Beem Africa, Africa's Talking, for a
Tanzanian deployment); this interface exists so a real provider drops in
later without touching any call site.
"""

from abc import ABC, abstractmethod


class SmsProvider(ABC):
    @abstractmethod
    def send(self, *, phone_number, message):
        """Send `message` to `phone_number`. Implementations should raise
        on a hard failure and no-op (not raise) on an unset/blank number.
        """


class NoOpSmsProvider(SmsProvider):
    """Documented no-op — logs nothing, sends nothing, never raises."""

    def send(self, *, phone_number, message):
        return None


sms_provider = NoOpSmsProvider()
