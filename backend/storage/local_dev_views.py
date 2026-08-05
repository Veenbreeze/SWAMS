"""Receiving end of `storage.local_dev`'s signed-upload-URL stand-in. The
mobile/web client PUTs raw bytes here exactly as it would to a real
Supabase Storage signed URL; this just writes them to `MEDIA_ROOT`.
Registered in `core/urls.py` only under `settings.DEBUG`.
"""

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["PUT"])
def local_storage_upload(request, bucket, path):
    if not settings.DEBUG:
        return HttpResponseNotFound()

    media_root = Path(settings.MEDIA_ROOT).resolve()
    destination = (media_root / bucket / path).resolve()
    # This endpoint has no auth (it stands in for a pre-signed URL, whose
    # signature is the credential) — reject anything that would resolve
    # outside MEDIA_ROOT rather than trust the path segments as-is.
    if media_root not in destination.parents:
        return HttpResponseBadRequest("Invalid path.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(request.body)
    return HttpResponse(status=204)
