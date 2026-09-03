"""Configuration loading and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from aws_automation.exceptions import ConfigError
from aws_automation.utils.validation import (
    validate_bucket_name,
    validate_instance_id,
    validate_region,
    validate_repository_name,
)

ALLOWED_TOP_LEVEL_KEYS = {"aws", "ec2", "s3", "ecr"}


@dataclass(frozen=True)
class AwsConfig:
    """AWS-related configuration values."""

    region: str | None = None


@dataclass(frozen=True)
class Ec2Config:
    """EC2-related configuration values."""

    instances: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class S3Config:
    """S3-related configuration values."""

    buckets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EcrConfig:
    """ECR-related configuration values."""

    repositories: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppConfig:
    """Application configuration."""

    aws: AwsConfig = field(default_factory=AwsConfig)
    ec2: Ec2Config = field(default_factory=Ec2Config)
    s3: S3Config = field(default_factory=S3Config)
    ecr: EcrConfig = field(default_factory=EcrConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        """Build configuration from a raw dictionary."""

        unknown_keys = set(data) - ALLOWED_TOP_LEVEL_KEYS
        if unknown_keys:
            keys = ", ".join(sorted(unknown_keys))
            raise ConfigError(f"Unsupported configuration section(s): {keys}.")

        aws_section = _get_mapping(data, "aws")
        ec2_section = _get_mapping(data, "ec2")
        s3_section = _get_mapping(data, "s3")
        ecr_section = _get_mapping(data, "ecr")

        aws_unknown = set(aws_section) - {"region"}
        if aws_unknown:
            keys = ", ".join(sorted(aws_unknown))
            raise ConfigError(
                f"Unsupported key(s) in 'aws': {keys}. Store credentials in AWS profiles, "
                "environment variables, or IAM roles instead of the config file."
            )

        ec2_unknown = set(ec2_section) - {"instances"}
        if ec2_unknown:
            keys = ", ".join(sorted(ec2_unknown))
            raise ConfigError(f"Unsupported key(s) in 'ec2': {keys}.")

        s3_unknown = set(s3_section) - {"buckets"}
        if s3_unknown:
            keys = ", ".join(sorted(s3_unknown))
            raise ConfigError(f"Unsupported key(s) in 's3': {keys}.")

        ecr_unknown = set(ecr_section) - {"repositories"}
        if ecr_unknown:
            keys = ", ".join(sorted(ecr_unknown))
            raise ConfigError(f"Unsupported key(s) in 'ecr': {keys}.")

        region = aws_section.get("region")
        if region is not None:
            _ensure_string(region, "aws.region")
            region = validate_region(region)

        instances = _read_string_list(ec2_section, "instances", "ec2.instances", validate_instance_id)
        buckets = _read_string_list(s3_section, "buckets", "s3.buckets", validate_bucket_name)
        repositories = _read_string_list(
            ecr_section,
            "repositories",
            "ecr.repositories",
            validate_repository_name,
        )

        return cls(
            aws=AwsConfig(region=region),
            ec2=Ec2Config(instances=instances),
            s3=S3Config(buckets=buckets),
            ecr=EcrConfig(repositories=repositories),
        )


def load_config(path: str | None) -> AppConfig:
    """Load and validate the YAML configuration file."""

    if path is None:
        return AppConfig()

    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Configuration file '{path}' was not found.")
    if not config_path.is_file():
        raise ConfigError(f"Configuration path '{path}' is not a file.")

    try:
        with config_path.open("r", encoding="utf-8") as handle:
            raw_config = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse YAML configuration '{path}': {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Unable to read configuration file '{path}': {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigError("The configuration file must contain a YAML mapping at the top level.")

    return AppConfig.from_dict(raw_config)


def _get_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"Configuration section '{key}' must be a mapping.")
    return value


def _ensure_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str):
        raise ConfigError(f"Configuration value '{field_name}' must be a string.")


def _read_string_list(
    section: dict[str, Any],
    key: str,
    field_name: str,
    validator: callable,
) -> list[str]:
    values = section.get(key, [])
    if values is None or values == []:
        return []
    if not isinstance(values, list):
        raise ConfigError(f"Configuration value '{field_name}' must be a list of strings.")

    validated: list[str] = []
    for index, value in enumerate(values, start=1):
        if not isinstance(value, str):
            raise ConfigError(
                f"Configuration value '{field_name}[{index}]' must be a string."
            )
        try:
            validated.append(validator(value))
        except Exception as exc:
            raise ConfigError(str(exc)) from exc
    return validated
