"""Private S3-compatible object storage used for ministry dataset uploads."""

from functools import lru_cache

import boto3

from .config import get_settings


class StorageNotConfigured(RuntimeError):
    pass


@lru_cache
def _client():
    settings = get_settings()
    if not settings.s3_bucket:
        raise StorageNotConfigured("S3_BUCKET must be configured for file uploads")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def put_private(key: str, payload: bytes, content_type: str) -> str:
    settings = get_settings()
    _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=payload, ContentType=content_type,
                         ServerSideEncryption="AES256")
    return f"{settings.s3_bucket}/{key}"


def get_private(key: str) -> bytes:
    settings = get_settings()
    response = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    try:
        body = response["Body"].read()
    finally:
        response["Body"].close()
    return body


def delete_private(key: str) -> None:
    settings = get_settings()
    _client().delete_object(Bucket=settings.s3_bucket, Key=key)
