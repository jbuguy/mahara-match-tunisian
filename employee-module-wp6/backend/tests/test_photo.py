import pytest

from app.services.photo import MAX_PHOTO_BYTES
from tests.test_profile import URL as PROFILE_URL
from tests.test_profile import codes, profile_body  # noqa: F401 (codes is a fixture)

URL = "/api/v1/me/photo"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 200 + b"\xff\xd9"


def upload(client, data: bytes, content_type: str = "image/jpeg"):
    return client.put(URL, files={"file": ("photo.jpg", data, content_type)})


@pytest.fixture
def with_profile(client, signed_in, codes):  # noqa: F811
    assert client.put(PROFILE_URL, json=profile_body(codes)).status_code == 200
    return codes


def test_photo_upload_then_read_back(client, with_profile):
    assert client.get(PROFILE_URL).json()["has_photo"] is False
    assert client.get(URL).status_code == 404

    assert upload(client, JPEG).status_code == 204

    response = client.get(URL)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == JPEG
    assert client.get(PROFILE_URL).json()["has_photo"] is True


def test_saving_the_profile_keeps_the_photo(client, with_profile):
    upload(client, JPEG)
    assert client.put(PROFILE_URL, json=profile_body(with_profile, full_name="Amira B.")).status_code == 200
    assert client.get(URL).content == JPEG


def test_photo_delete_goes_back_to_none(client, with_profile):
    upload(client, JPEG)
    assert client.delete(URL).status_code == 204
    assert client.get(URL).status_code == 404
    assert client.get(PROFILE_URL).json()["has_photo"] is False


def test_photo_rejects_non_jpeg(client, with_profile):
    response = upload(client, b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")
    assert response.status_code == 415


def test_photo_rejects_large_file(client, with_profile):
    response = upload(client, JPEG[:4] + b"\x00" * MAX_PHOTO_BYTES)
    assert response.status_code == 413


def test_photo_needs_a_profile_first(client, signed_in):
    assert upload(client, JPEG).status_code == 404
    assert client.delete(URL).status_code == 404


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_photo_requires_login(client, signed_out, method):
    response = client.request(method.upper(), URL)
    assert response.status_code == 401
