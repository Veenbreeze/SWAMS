"""A Django email backend that sends via Resend's HTTPS API instead of raw
SMTP — see docs/06-RUNBOOK.md. Render's free web services block outbound
traffic to SMTP ports (25/465/587) entirely as of September 2025, so
Django's built-in `smtp.EmailBackend` cannot work there regardless of
credentials; a plain HTTPS POST is unaffected by that block. Uses stdlib
`urllib` rather than adding a `requests`/`httpx` dependency, matching
`storage/supabase_client.py`'s reasoning for the same choice.

Without a verified sending domain on the Resend account, Resend only
delivers to the account owner's own verified address — see
RESEND_FROM_EMAIL's docstring in settings.
"""

import json
import urllib.request
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

_API_URL = "https://api.resend.com/emails"


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            if self._send_one(message):
                sent_count += 1
        return sent_count

    def _send_one(self, message):
        payload = {
            "from": message.from_email,
            "to": list(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)

        request = urllib.request.Request(
            _API_URL,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
                # Cloudflare (in front of Resend's API) blocks requests with
                # urllib's default "Python-urllib/x.y" User-Agent as a bot
                # signature (its own error code 1010) before they ever reach
                # Resend — confirmed by reproducing a 403 without this and a
                # success with it.
                "User-Agent": "SWAMS-Backend/1.0",
            },
            data=json.dumps(payload).encode(),
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                return True
        except (HTTPError, URLError):
            if not self.fail_silently:
                raise
            return False
