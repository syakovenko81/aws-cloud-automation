"""Command-line interface for aws_automation."""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from typing import Sequence

from aws_automation.aws_session import create_client, create_session
from aws_automation.config import AppConfig, load_config
from aws_automation.exceptions import AppError, ValidationError
from aws_automation.services.ec2 import EC2Service
from aws_automation.services.ecr import ECRService
from aws_automation.services.s3 import S3Service
from aws_automation.utils.logging import configure_logging
from aws_automation.utils.validation import (
    validate_bucket_name,
    validate_instance_id,
    validate_region,
    validate_repository_name,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeContext:
    """Runtime options resolved from CLI arguments and configuration."""

    config: AppConfig
    region: str | None
    profile: str | None
    dry_run: bool


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level CLI parser."""

    parser = argparse.ArgumentParser(
        prog="aws-automation",
        description="Manage EC2, S3, and ECR resources from one CLI.",
    )
    parser.add_argument("--config", help="Path to a YAML configuration file.")
    parser.add_argument("--region", help="Override the AWS region.")
    parser.add_argument("--profile", help="Use a named AWS CLI profile.")
    parser.add_argument("--verbose", action="store_true", help="Enable DEBUG logging.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what a mutating command would do without calling the AWS API.",
    )

    service_parsers = parser.add_subparsers(dest="service", required=True)

    _build_ec2_parser(service_parsers)
    _build_s3_parser(service_parsers)
    _build_ecr_parser(service_parsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    try:
        config = load_config(args.config)
        context = RuntimeContext(
            config=config,
            region=_resolve_region(args.region, config),
            profile=args.profile,
            dry_run=args.dry_run,
        )

        logger.debug(
            "Resolved runtime context: config=%s profile=%s region=%s dry_run=%s",
            args.config,
            context.profile,
            context.region,
            context.dry_run,
        )

        return dispatch(args, context)
    except AppError as exc:
        logger.error(str(exc))
        return exc.exit_code
    except KeyboardInterrupt:
        logger.error("Operation interrupted by user.")
        return 130


def dispatch(args: argparse.Namespace, context: RuntimeContext) -> int:
    """Route the parsed command to the correct handler."""

    if args.service == "ec2":
        return _handle_ec2(args, context)
    if args.service == "s3":
        return _handle_s3(args, context)
    if args.service == "ecr":
        return _handle_ecr(args, context)
    raise ValidationError(f"Unsupported service '{args.service}'.")


def _build_ec2_parser(service_parsers: argparse._SubParsersAction) -> None:
    ec2_parser = service_parsers.add_parser("ec2", help="Manage EC2 instances.")
    ec2_commands = ec2_parser.add_subparsers(dest="command", required=True)

    ec2_list = ec2_commands.add_parser("list", help="List EC2 instances.")
    ec2_list.add_argument(
        "--instance-id",
        dest="instance_ids",
        action="append",
        help="EC2 instance ID to include. Repeat the option to include multiple instances.",
    )

    ec2_start = ec2_commands.add_parser("start", help="Start EC2 instances.")
    ec2_start.add_argument(
        "--instance-id",
        dest="instance_ids",
        action="append",
        help="EC2 instance ID to start. Repeat the option to start multiple instances.",
    )

    ec2_restart = ec2_commands.add_parser("restart", help="Restart EC2 instances.")
    ec2_restart.add_argument(
        "--instance-id",
        dest="instance_ids",
        action="append",
        help="EC2 instance ID to restart. Repeat the option to restart multiple instances.",
    )

    ec2_stop = ec2_commands.add_parser("stop", help="Stop EC2 instances.")
    ec2_stop.add_argument(
        "--instance-id",
        dest="instance_ids",
        action="append",
        help="EC2 instance ID to stop. Repeat the option to stop multiple instances.",
    )


def _build_s3_parser(service_parsers: argparse._SubParsersAction) -> None:
    s3_parser = service_parsers.add_parser("s3", help="Manage S3 resources.")
    s3_commands = s3_parser.add_subparsers(dest="command", required=True)

    s3_commands.add_parser("list-buckets", help="List S3 buckets.")

    s3_list_objects = s3_commands.add_parser("list-objects", help="List objects in a bucket.")
    s3_list_objects.add_argument("--bucket", help="Bucket name.")


def _build_ecr_parser(service_parsers: argparse._SubParsersAction) -> None:
    ecr_parser = service_parsers.add_parser("ecr", help="Manage ECR resources.")
    ecr_commands = ecr_parser.add_subparsers(dest="command", required=True)

    ecr_commands.add_parser("list-repositories", help="List ECR repositories.")

    ecr_list_images = ecr_commands.add_parser("list-images", help="List images in a repository.")
    ecr_list_images.add_argument("--repository", help="ECR repository name.")


def _handle_ec2(args: argparse.Namespace, context: RuntimeContext) -> int:
    if args.command == "list":
        session = create_session(profile=context.profile, region=context.region)
        service = EC2Service(create_client(session, "ec2"))
        instance_ids = _resolve_instance_ids(args.instance_ids, context.config, required=False)
        rows = service.list_instances(instance_ids=instance_ids)
        _print_table(["Instance ID", "State", "Type"], rows, empty_message="No EC2 instances found.")
        return 0

    instance_ids = _resolve_instance_ids(args.instance_ids, context.config, required=True)
    if args.command == "start":
        if context.dry_run:
            for instance_id in instance_ids:
                print(f"DRY RUN: EC2 instance {instance_id} would be started.")
            print("No changes were made.")
            return 0

        session = create_session(profile=context.profile, region=context.region)
        service = EC2Service(create_client(session, "ec2"))
        rows = service.start_instances(instance_ids)
        _print_table(
            ["Instance ID", "Previous State", "Current State"],
            rows,
            empty_message="No EC2 instances were started.",
        )
        return 0

    if args.command == "restart":
        if context.dry_run:
            for instance_id in instance_ids:
                print(f"DRY RUN: EC2 instance {instance_id} would be restarted.")
            print("No changes were made.")
            return 0

        session = create_session(profile=context.profile, region=context.region)
        service = EC2Service(create_client(session, "ec2"))
        rows = service.restart_instances(instance_ids)
        _print_table(
            ["Instance ID", "Action"],
            rows,
            empty_message="No EC2 instances were restarted.",
        )
        return 0

    if args.command == "stop":
        if context.dry_run:
            for instance_id in instance_ids:
                print(f"DRY RUN: EC2 instance {instance_id} would be stopped.")
            print("No changes were made.")
            return 0

        session = create_session(profile=context.profile, region=context.region)
        service = EC2Service(create_client(session, "ec2"))
        rows = service.stop_instances(instance_ids)
        _print_table(
            ["Instance ID", "Previous State", "Current State"],
            rows,
            empty_message="No EC2 instances were stopped.",
        )
        return 0

    raise ValidationError(f"Unsupported EC2 command '{args.command}'.")


def _handle_s3(args: argparse.Namespace, context: RuntimeContext) -> int:
    session = create_session(profile=context.profile, region=context.region)
    service = S3Service(create_client(session, "s3"))

    if args.command == "list-buckets":
        rows = service.list_buckets()
        _print_table(["Bucket", "Created"], rows, empty_message="No S3 buckets found.")
        return 0

    if args.command == "list-objects":
        bucket_name = _resolve_bucket_name(args.bucket, context.config)
        rows = service.list_objects(bucket_name)
        _print_table(
            ["Key", "Size", "Last Modified"],
            rows,
            empty_message=f"No objects found in bucket '{bucket_name}'.",
        )
        return 0

    raise ValidationError(f"Unsupported S3 command '{args.command}'.")


def _handle_ecr(args: argparse.Namespace, context: RuntimeContext) -> int:
    session = create_session(profile=context.profile, region=context.region)
    service = ECRService(create_client(session, "ecr"))

    if args.command == "list-repositories":
        rows = service.list_repositories()
        _print_table(["Repository", "URI"], rows, empty_message="No ECR repositories found.")
        return 0

    if args.command == "list-images":
        repository_name = _resolve_repository_name(args.repository, context.config)
        rows = service.list_images(repository_name)
        _print_table(
            ["Tags", "Digest", "Pushed At"],
            rows,
            empty_message=f"No images found in repository '{repository_name}'.",
        )
        return 0

    raise ValidationError(f"Unsupported ECR command '{args.command}'.")


def _resolve_region(cli_region: str | None, config: AppConfig) -> str | None:
    region = cli_region or config.aws.region
    if region is None:
        return None
    return validate_region(region)


def _resolve_instance_ids(
    cli_instance_ids: list[str] | None,
    config: AppConfig,
    *,
    required: bool,
) -> list[str] | None:
    instance_ids = cli_instance_ids or config.ec2.instances
    if not instance_ids:
        if required:
            raise ValidationError(
                "At least one EC2 instance ID is required. Provide --instance-id or define "
                "ec2.instances in the configuration file."
            )
        return None
    return [validate_instance_id(instance_id) for instance_id in instance_ids]


def _resolve_bucket_name(cli_bucket: str | None, config: AppConfig) -> str:
    if cli_bucket:
        return validate_bucket_name(cli_bucket)

    if len(config.s3.buckets) == 1:
        return config.s3.buckets[0]

    if len(config.s3.buckets) > 1:
        raise ValidationError(
            "Bucket name is required because multiple buckets are configured. Use --bucket."
        )

    raise ValidationError(
        "Bucket name is required. Provide --bucket or define one bucket in s3.buckets."
    )


def _resolve_repository_name(cli_repository: str | None, config: AppConfig) -> str:
    if cli_repository:
        return validate_repository_name(cli_repository)

    if len(config.ecr.repositories) == 1:
        return config.ecr.repositories[0]

    if len(config.ecr.repositories) > 1:
        raise ValidationError(
            "Repository name is required because multiple repositories are configured. "
            "Use --repository."
        )

    raise ValidationError(
        "Repository name is required. Provide --repository or define one repository in "
        "ecr.repositories."
    )


def _print_table(headers: list[str], rows: list[dict[str, str]], *, empty_message: str) -> None:
    if not rows:
        print(empty_message)
        return

    widths = [len(header) for header in headers]
    for row in rows:
        for index, header in enumerate(headers):
            widths[index] = max(widths[index], len(str(row.get(header, "-"))))

    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    for row in rows:
        print(
            "  ".join(
                str(row.get(header, "-")).ljust(widths[index])
                for index, header in enumerate(headers)
            )
        )
