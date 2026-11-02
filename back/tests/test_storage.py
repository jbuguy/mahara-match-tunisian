from types import SimpleNamespace

import pytest

from app import storage


class FakePaginator:
    def paginate(self, **kwargs):
        assert kwargs == {"Bucket": "candidate-files", "Prefix": "cv.pdf"}
        return [
            {
                "Versions": [
                    {"Key": "cv.pdf", "VersionId": "old"},
                    {"Key": "cv.pdf.backup", "VersionId": "unrelated"},
                ],
                "DeleteMarkers": [{"Key": "cv.pdf", "VersionId": "marker"}],
            }
        ]


class FakeS3:
    def __init__(self, response=None):
        self.response = response or {}
        self.deletions = []

    def get_paginator(self, operation):
        assert operation == "list_object_versions"
        return FakePaginator()

    def delete_objects(self, **kwargs):
        self.deletions.append(kwargs)
        return self.response


def test_purge_private_deletes_all_versions_and_markers_for_exact_key(monkeypatch):
    client = FakeS3()
    monkeypatch.setattr(storage, "_client", lambda: client)
    monkeypatch.setattr(storage, "get_settings", lambda: SimpleNamespace(s3_bucket="candidate-files"))

    storage.purge_private("cv.pdf")

    assert client.deletions == [
        {
            "Bucket": "candidate-files",
            "Delete": {
                "Objects": [
                    {"Key": "cv.pdf", "VersionId": "old"},
                    {"Key": "cv.pdf", "VersionId": "marker"},
                ],
                "Quiet": True,
            },
        }
    ]


def test_purge_private_surfaces_storage_errors(monkeypatch):
    client = FakeS3(response={"Errors": [{"Key": "cv.pdf", "Code": "AccessDenied"}]})
    monkeypatch.setattr(storage, "_client", lambda: client)
    monkeypatch.setattr(storage, "get_settings", lambda: SimpleNamespace(s3_bucket="candidate-files"))

    with pytest.raises(RuntimeError, match="Object version purge failed"):
        storage.purge_private("cv.pdf")
