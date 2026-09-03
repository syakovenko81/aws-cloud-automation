"""ECR service operations."""

from __future__ import annotations

from datetime import datetime

from botocore.exceptions import BotoCoreError, ClientError

from aws_automation.aws_session import translate_boto_error


class ECRService:
    """Service wrapper for ECR operations."""

    def __init__(self, client) -> None:
        self.client = client

    def list_repositories(self) -> list[dict[str, str]]:
        """List ECR repositories."""

        try:
            paginator = self.client.get_paginator("describe_repositories")
            pages = paginator.paginate()
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        results: list[dict[str, str]] = []
        try:
            for page in pages:
                for repository in page.get("repositories", []):
                    results.append(
                        {
                            "Repository": repository.get("repositoryName", "-"),
                            "URI": repository.get("repositoryUri", "-"),
                        }
                    )
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc
        return results

    def list_images(self, repository_name: str) -> list[dict[str, str]]:
        """List images in an ECR repository."""

        try:
            paginator = self.client.get_paginator("describe_images")
            pages = paginator.paginate(repositoryName=repository_name)
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        results: list[dict[str, str]] = []
        try:
            for page in pages:
                for details in page.get("imageDetails", []):
                    tags = ", ".join(details.get("imageTags", [])) or "<untagged>"
                    results.append(
                        {
                            "Tags": tags,
                            "Digest": details.get("imageDigest", "-"),
                            "Pushed At": _format_datetime(details.get("imagePushedAt")),
                        }
                    )
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc
        return results


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")

