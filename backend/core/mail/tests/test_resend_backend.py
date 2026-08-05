import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest
from django.core.mail import EmailMessage
from django.test import override_settings

from core.mail.resend_backend import ResendEmailBackend

pytestmark = pytest.mark.django_db


@override_settings(RESEND_API_KEY="re_test_key")
@patch("core.mail.resend_backend.urllib.request.urlopen")
def test_sends_one_message_and_returns_count(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value = MagicMock()
    message = EmailMessage(
        subject="Reset your password",
        body="Use this link...",
        from_email="no-reply@swams.app",
        to=["employee@example.com"],
    )

    sent = ResendEmailBackend().send_messages([message])

    assert sent == 1
    request = mock_urlopen.call_args.args[0]
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer re_test_key"
    body = json.loads(request.data)
    assert body["to"] == ["employee@example.com"]
    assert body["subject"] == "Reset your password"


@override_settings(RESEND_API_KEY="re_test_key")
@patch("core.mail.resend_backend.urllib.request.urlopen")
def test_no_messages_returns_zero_without_a_request(mock_urlopen):
    sent = ResendEmailBackend().send_messages([])

    assert sent == 0
    mock_urlopen.assert_not_called()


@override_settings(RESEND_API_KEY="re_test_key")
@patch("core.mail.resend_backend.urllib.request.urlopen")
def test_fail_silently_swallows_the_error(mock_urlopen):
    mock_urlopen.side_effect = HTTPError("url", 422, "Unprocessable", {}, None)
    message = EmailMessage(
        subject="s", body="b", from_email="no-reply@swams.app", to=["e@example.com"]
    )

    backend = ResendEmailBackend(fail_silently=True)
    sent = backend.send_messages([message])

    assert sent == 0


@override_settings(RESEND_API_KEY="re_test_key")
@patch("core.mail.resend_backend.urllib.request.urlopen")
def test_raises_when_not_failing_silently(mock_urlopen):
    mock_urlopen.side_effect = HTTPError("url", 422, "Unprocessable", {}, None)
    message = EmailMessage(
        subject="s", body="b", from_email="no-reply@swams.app", to=["e@example.com"]
    )

    backend = ResendEmailBackend(fail_silently=False)
    with pytest.raises(HTTPError):
        backend.send_messages([message])
