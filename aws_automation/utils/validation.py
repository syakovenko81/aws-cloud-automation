"""Validation helpers for CLI arguments and configuration values."""

from __future__ import annotations

import re

from aws_automation.exceptions import ValidationError

REGION_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z]+)+-\d$")
INSTANCE_ID_PATTERN = re.compile(r"^i-(?:[0-9a-f]{8}|[0-9a-f]{17})$")
BUCKET_PATTERN = re.compile(r"^(?![.-])[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
REPOSITORY_PATTERN = re.compile(r"^[a-z0-9]+(?:(?:[._/-])[a-z0-9]+)*$")


def validate_region(region: str) -> str:
    """Validate an AWS region name."""

    if not REGION_PATTERN.fullmatch(region):
        raise ValidationError(
            f"Invalid AWS region '{region}'. Example valid values: eu-central-1, us-east-1."
        )
    return region


def validate_instance_id(instance_id: str) -> str:
    """Validate an EC2 instance ID."""

    if not INSTANCE_ID_PATTERN.fullmatch(instance_id):
        raise ValidationError(
            f"Invalid EC2 instance ID '{instance_id}'. Expected a value like i-0123456789abcdef0."
        )
    return instance_id


def validate_bucket_name(bucket_name: str) -> str:
    """Validate an S3 bucket name."""

    if not BUCKET_PATTERN.fullmatch(bucket_name):
        raise ValidationError(
            f"Invalid S3 bucket name '{bucket_name}'. Bucket names must be 3-63 characters "
            "and use lowercase letters, numbers, dots, or hyphens."
        )
    return bucket_name


def validate_repository_name(repository_name: str) -> str:
    """Validate an ECR repository name."""

    if not REPOSITORY_PATTERN.fullmatch(repository_name):
        raise ValidationError(
            f"Invalid ECR repository name '{repository_name}'. "
            "Use lowercase letters, numbers, and separators such as '/', '-', '_', or '.'."
        )
    return repository_name


def validate_non_empty_list(values: list[str], label: str) -> list[str]:
    """Validate a non-empty list of string values."""

    if not values:
        raise ValidationError(f"{label} must not be empty.")
    return values

