"""Supabase Storage signed-upload-URL issuance — see
docs/01-SYSTEM-ARCHITECTURE.md §6.5.

Uploads never pass through Django as multipart request bodies: the backend
issues a short-lived signed URL and the client PUTs the file to Supabase
directly. `_request_signed_upload_url` is the one place that makes the
actual HTTP call, isolated behind `create_signed_upload_path` so callers
(and tests, via `unittest.mock.patch`) never need a real Supabase project
or a mocked HTTP layer — no `requests`/`httpx` dependency was added since
this is the only caller and stdlib `urllib` is enough for one POST.
"""

import json
import urllib.request
import uuid
from urllib.error import HTTPError, URLError

from django.conf import settings


class StorageNotConfiguredError(Exception):
    """SUPABASE_URL/SUPABASE_SERVICE_KEY are unset — expected in local dev
    without a provisioned Supabase project; callers should surface this as
    a clear "storage unavailable" error rather than a raw network failure.
    """


class StorageRequestError(Exception):
    """Supabase Storage API reachable but returned an error response."""


def _request_signed_upload_url(*, bucket, path):
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise StorageNotConfiguredError("SUPABASE_URL/SUPABASE_SERVICE_KEY are not configured.")

    url = f"{settings.SUPABASE_URL}/storage/v1/object/upload/sign/{bucket}/{path}"
    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        },
        data=b"{}",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read())
    except (HTTPError, URLError) as exc:
        raise StorageRequestError(f"Supabase Storage request failed: {exc}") from exc

    return f"{settings.SUPABASE_URL}/storage/v1{body['url']}"


def create_signed_upload_path(*, bucket, path_prefix, extension):
    """Builds a server-generated, non-client-supplied storage path (see
    §6.5 "filenames are never client-supplied") and requests a signed
    upload URL for it.

    Returns `(upload_url, path)`.
    """
    filename = f"{uuid.uuid4()}.{extension}"
    path = f"{path_prefix}/{filename}"
    upload_url = _request_signed_upload_url(bucket=bucket, path=path)
    return upload_url, path


def public_url(*, bucket, path):
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def upload_object(*, bucket, path, content, content_type):
    """Direct server-side upload (as opposed to `create_signed_upload_path`,
    which issues a URL for a *client* to upload to). Used for files the
    backend itself generates — e.g. report exports (Phase 6) — where
    there's no untrusted client upload to keep out of Django's request
    body in the first place.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise StorageNotConfiguredError("SUPABASE_URL/SUPABASE_SERVICE_KEY are not configured.")

    url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        data=content,
    )
    try:
        with urllib.request.urlopen(request, timeout=30):
            pass
    except (HTTPError, URLError) as exc:
        raise StorageRequestError(f"Supabase Storage upload failed: {exc}") from exc


def create_signed_download_url(*, bucket, path, expires_in=3600):
    """A time-limited READ url for a file already in storage — the
    download-side counterpart to `create_signed_upload_path`'s upload-side
    signed URL. A different Supabase Storage API endpoint
    (`/object/sign/...`, not `/object/upload/sign/...`).
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise StorageNotConfiguredError("SUPABASE_URL/SUPABASE_SERVICE_KEY are not configured.")

    url = f"{settings.SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}"
    request = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps({"expiresIn": expires_in}).encode(),
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = json.loads(response.read())
    except (HTTPError, URLError) as exc:
        raise StorageRequestError(f"Supabase Storage request failed: {exc}") from exc

    return f"{settings.SUPABASE_URL}/storage/v1{body['signedURL']}"
