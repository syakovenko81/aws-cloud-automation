"""S3 service operations."""

from __future__ import annotations

from datetime import datetime

from botocore.exceptions import BotoCoreError, ClientError

from aws_automation.aws_session import translate_boto_error


class S3Service:
    """Service wrapper for S3 operations."""

    def __init__(self, client) -> None:
        self.client = client

    def list_buckets(self) -> list[dict[str, str]]:
        """List S3 buckets accessible to the current identity."""

        try:
            response = self.client.list_buckets()
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        results: list[dict[str, str]] = []
        for bucket in response.get("Buckets", []):
            created = bucket.get("CreationDate")
            results.append(
                {
                    "Bucket": bucket.get("Name", "-"),
                    "Created": _format_datetime(created),
                }
            )
        return results

    def list_objects(self, bucket_name: str) -> list[dict[str, str]]:
        """List objects in an S3 bucket."""

        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=bucket_name)
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        results: list[dict[str, str]] = []
        try:
            for page in pages:
                for item in page.get("Contents", []):
                    results.append(
                        {
                            "Key": item.get("Key", "-"),
                            "Size": str(item.get("Size", 0)),
                            "Last Modified": _format_datetime(item.get("LastModified")),
                        }
                    )
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc
        return results


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")

