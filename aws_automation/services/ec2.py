"""EC2 service operations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from aws_automation.aws_session import translate_boto_error


class EC2Service:
    """Service wrapper for EC2 operations."""

    def __init__(self, client) -> None:
        self.client = client

    def list_instances(self, instance_ids: Iterable[str] | None = None) -> list[dict[str, str]]:
        """List EC2 instances."""

        params: dict[str, Any] = {}
        normalized_ids = list(instance_ids or [])
        if normalized_ids:
            params["InstanceIds"] = normalized_ids

        try:
            paginator = self.client.get_paginator("describe_instances")
            pages = paginator.paginate(**params)
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        results: list[dict[str, str]] = []
        try:
            for page in pages:
                for reservation in page.get("Reservations", []):
                    for instance in reservation.get("Instances", []):
                        results.append(
                            {
                                "Instance ID": instance.get("InstanceId", "-"),
                                "State": instance.get("State", {}).get("Name", "-"),
                                "Type": instance.get("InstanceType", "-"),
                            }
                        )
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc
        return results

    def start_instances(self, instance_ids: list[str], dry_run: bool = False) -> list[dict[str, str]]:
        """Start one or more EC2 instances."""

        if dry_run:
            return [{"Instance ID": instance_id, "Action": "would be started"} for instance_id in instance_ids]

        try:
            response = self.client.start_instances(InstanceIds=instance_ids)
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        return [
            {
                "Instance ID": change["InstanceId"],
                "Previous State": change["PreviousState"]["Name"],
                "Current State": change["CurrentState"]["Name"],
            }
            for change in response.get("StartingInstances", [])
        ]

    def stop_instances(self, instance_ids: list[str], dry_run: bool = False) -> list[dict[str, str]]:
        """Stop one or more EC2 instances."""

        if dry_run:
            return [{"Instance ID": instance_id, "Action": "would be stopped"} for instance_id in instance_ids]

        try:
            response = self.client.stop_instances(InstanceIds=instance_ids)
        except (ClientError, BotoCoreError) as exc:
            raise translate_boto_error(exc) from exc

        return [
            {
                "Instance ID": change["InstanceId"],
                "Previous State": change["PreviousState"]["Name"],
                "Current State": change["CurrentState"]["Name"],
            }
            for change in response.get("StoppingInstances", [])
        ]

