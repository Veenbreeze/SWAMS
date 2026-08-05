import pytest
from django.test import RequestFactory, override_settings
from rest_framework.test import APIClient

from storage.local_dev_views import local_storage_upload

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True)
def test_put_writes_file_under_media_root(tmp_path):
    # Uses RequestFactory (calls the view directly, no middleware chain)
    # rather than the full test Client — going through Client with
    # DEBUG=True also activates debug_toolbar's middleware, whose own
    # URLs are never registered under pytest-django's forced DEBUG=False
    # at urlconf import time, which fails unrelated to this view.
    with override_settings(MEDIA_ROOT=tmp_path):
        request = RequestFactory().put(
            "/api/v1/dev/local-storage/profile-pictures/org-id/emp-id/photo.jpg",
            data=b"fake-image-bytes",
            content_type="image/jpeg",
        )
        response = local_storage_upload(
            request, bucket="profile-pictures", path="org-id/emp-id/photo.jpg"
        )

        assert response.status_code == 204
        written = tmp_path / "profile-pictures" / "org-id" / "emp-id" / "photo.jpg"
        assert written.read_bytes() == b"fake-image-bytes"


@override_settings(DEBUG=True)
def test_rejects_path_traversal_outside_media_root(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        request = RequestFactory().put(
            "/api/v1/dev/local-storage/profile-pictures/../../../etc/passwd",
            data=b"malicious",
            content_type="text/plain",
        )
        response = local_storage_upload(
            request, bucket="profile-pictures", path="../../../etc/passwd"
        )

        assert response.status_code == 400
        assert not (tmp_path.parent.parent.parent / "etc" / "passwd").exists()


def test_returns_404_outside_debug(tmp_path):
    # pytest-django already forces settings.DEBUG False for the whole
    # session by default — this is the real, unforced state.
    with override_settings(MEDIA_ROOT=tmp_path):
        client = APIClient()
        response = client.put(
            "/api/v1/dev/local-storage/profile-pictures/org-id/emp-id/photo.jpg",
            data=b"fake-image-bytes",
            content_type="image/jpeg",
        )

        assert response.status_code == 404
