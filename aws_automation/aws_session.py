"""AWS session and client creation."""

from __future__ import annotations

import logging

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    NoRegionError,
    ParamValidationError,
    ProfileNotFound,
)

from aws_automation.exceptions import AWSServiceError

logger = logging.getLogger(__name__)


def create_session(profile: str | None = None, region: str | None = None) -> boto3.Session:
    """Create a Boto3 session using the standard credential provider chain."""

    logger.debug("Creating AWS session with profile=%s region=%s", profile, region)
    try:
        return boto3.Session(profile_name=profile, region_name=region)
    except ProfileNotFound as exc:
        raise AWSServiceError(f"AWS profile '{profile}' was not found.") from exc


def create_client(session: boto3.Session, service_name: str):
    """Create a Boto3 client from a session."""

    try:
        return session.client(service_name)
    except (BotoCoreError, ProfileNotFound) as exc:
        raise translate_boto_error(exc) from exc


def translate_boto_error(error: Exception) -> AWSServiceError:
    """Translate a botocore exception into a user-friendly application error."""

    if isinstance(error, ProfileNotFound):
        return AWSServiceError(f"AWS profile '{error.profile}' was not found.")

    if isinstance(error, NoCredentialsError):
        return AWSServiceError(
            "AWS credentials were not found. Configure an AWS CLI profile, environment "
            "variables, or an IAM role."
        )

    if isinstance(error, NoRegionError):
        return AWSServiceError(
            "No AWS region is configured. Use --region, config/example.yaml, or a default "
            "region in your AWS profile."
        )

    if isinstance(error, EndpointConnectionError):
        return AWSServiceError(
            "Unable to reach the AWS endpoint. Check the configured region and network access."
        )

    if isinstance(error, ParamValidationError):
        return AWSServiceError(f"Invalid AWS request parameters: {error}", exit_code=2)

    if isinstance(error, ClientError):
        details = error.response.get("Error", {})
        code = details.get("Code", "Unknown")
        message = details.get("Message", "No additional details were provided by AWS.")

        if code in {
            "AuthFailure",
            "ExpiredToken",
            "InvalidClientTokenId",
            "SignatureDoesNotMatch",
            "UnrecognizedClientException",
        }:
            return AWSServiceError(
                "AWS authentication failed. Check the selected profile, environment variables, "
                "or IAM role."
            )

        if code in {
            "AccessDenied",
            "AccessDeniedException",
            "UnauthorizedOperation",
        }:
            return AWSServiceError(
                "AWS request was denied. Check the IAM permissions for the current identity.",
                exit_code=5,
            )

        if code in {
            "InvalidInstanceID.NotFound",
            "NoSuchBucket",
            "RepositoryNotFoundException",
        }:
            return AWSServiceError(f"Requested AWS resource was not found: {message}", exit_code=6)

        if code in {
            "InvalidParameterValue",
            "InvalidParameterException",
            "ValidationException",
        }:
            return AWSServiceError(f"Invalid AWS request: {message}", exit_code=2)

        return AWSServiceError(f"AWS API error ({code}): {message}", exit_code=6)

    if isinstance(error, BotoCoreError):
        return AWSServiceError(f"AWS SDK error: {error}", exit_code=6)

    return AWSServiceError(str(error), exit_code=6)

