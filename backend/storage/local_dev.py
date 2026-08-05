"""Local-dev-only stand-in for `supabase_client`'s signed-upload-URL flow.

`supabase_client.create_signed_upload_path` deliberately raises
`StorageNotConfiguredError` when `SUPABASE_URL`/`SUPABASE_SERVICE_KEY`
aren't set — expected without a provisioned Supabase project. This module
mirrors its `(upload_url, path)` shape but points the client at this
machine's own dev server (`storage.local_dev_views.local_storage_upload`,
registered only under `settings.DEBUG`) and writes to `MEDIA_ROOT` instead
of real object storage. Only ever invoked from
`apps.employees.services.request_profile_picture_upload` when Supabase
isn't configured AND `DEBUG` is True — never reachable in production.
"""

import uuid

from django.conf import settings


def create_local_upload_path(*, bucket, path_prefix, extension):
    filename = f"{uuid.uuid4()}.{extension}"
    path = f"{path_prefix}/{filename}"
    base = settings.LOCAL_DEV_PUBLIC_BASE_URL.rstrip("/")
    upload_url = f"{base}/api/v1/dev/local-storage/{bucket}/{path}"
    return upload_url, path


def local_public_url(*, bucket, path):
    base = settings.LOCAL_DEV_PUBLIC_BASE_URL.rstrip("/")
    return f"{base}{settings.MEDIA_URL}{bucket}/{path}"
