# aws-cloud-automation

`aws-cloud-automation` is a small DevOps automation exercise written in Python. It provides a unified CLI and YAML configuration file for a focused set of AWS operations across EC2, S3, and ECR using Boto3.

The goal is to demonstrate clean Python structure, configuration management, input validation, logging, dry-run behavior, and AWS SDK integration without over-engineering the project. It is not described here as production-ready software.

## Features

- Unified CLI for EC2, S3, and ECR
- YAML configuration file with CLI overrides
- Standard Boto3 credential provider chain
- Input validation for regions and resource identifiers
- Clear user-facing error handling
- Global `--dry-run` support for mutating EC2 commands
- Modular service classes with injectable AWS clients for future pytest-based tests

## Project structure

```text
.
├── .gitignore
├── README.md
├── config
│   └── example.yaml
├── pyproject.toml
├── requirements.txt
├── src
│   └── aws_automation
│       ├── __init__.py
│       ├── __main__.py
│       ├── aws_session.py
│       ├── cli.py
│       ├── config.py
│       ├── exceptions.py
│       ├── services
│       │   ├── __init__.py
│       │   ├── ec2.py
│       │   ├── ecr.py
│       │   └── s3.py
│       └── utils
│           ├── __init__.py
│           ├── logging.py
│           └── validation.py
└── tests
    └── __init__.py
```

## Architecture

### Module responsibilities

- `cli.py`: builds the argparse CLI, resolves configuration overrides, dispatches commands, and formats human-readable output
- `config.py`: loads YAML configuration, validates structure and values, and returns typed configuration objects
- `aws_session.py`: creates Boto3 sessions and clients, and translates botocore exceptions into user-friendly application errors
- `services/ec2.py`: EC2 list, start, restart, and stop operations
- `services/s3.py`: S3 bucket and object listing operations
- `services/ecr.py`: ECR repository and image listing operations
- `utils/validation.py`: reusable validation for regions, instance IDs, bucket names, and repository names
- `utils/logging.py`: application logging setup
- `exceptions.py`: small hierarchy for configuration, validation, and AWS operation errors

### Design choices

- The CLI layer is intentionally thin and delegates AWS-specific logic to service classes.
- Service classes accept injected Boto3 clients so future tests can mock AWS interactions cleanly.
- Configuration is optional. When present, it provides defaults that command-line arguments can override.
- Only a small set of public behaviors is implemented to keep the exercise understandable during a technical assessment.

## Requirements

- Python 3.10+
- AWS credentials available through the normal AWS mechanisms

## Installation

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

For local development, install the package in editable mode so `python -m aws_automation` and `aws-automation` work consistently:

```bash
python -m pip install -e .
```

## AWS authentication

This project uses the standard Boto3 credential provider chain. Do not place credentials in the YAML configuration file.

Supported credential sources include:

- AWS CLI profiles
- environment variables
- IAM roles

Examples:

```bash
python -m aws_automation --profile my-profile ec2 list
aws-automation --profile my-profile s3 list-buckets
```

## Configuration

Example configuration:

```yaml
aws:
  region: eu-central-1

ec2:
  instances:
    - i-0123456789abcdef0
    - i-0123456789abcdef1

s3:
  buckets:
    - my-test-bucket

ecr:
  repositories:
    - my-application
```

Rules:

- `aws.region` is optional and can be overridden by `--region`
- `ec2.instances` can be used as default targets for `ec2 list`, `ec2 start`, `ec2 restart`, and `ec2 stop`
- `s3.buckets` and `ecr.repositories` can provide default targets when exactly one value is configured
- credentials are intentionally not supported in the configuration file

## CLI usage

Top-level help:

```bash
python -m aws_automation --help
python -m aws_automation ec2 --help
python -m aws_automation s3 --help
python -m aws_automation ecr --help
```

EC2:

```bash
python -m aws_automation ec2 list
python -m aws_automation ec2 list --state running
python -m aws_automation ec2 list --instance-id i-0123456789abcdef0
python -m aws_automation ec2 start --instance-id i-0123456789abcdef0
python -m aws_automation ec2 restart --instance-id i-0123456789abcdef0
python -m aws_automation ec2 stop --instance-id i-0123456789abcdef0
```

S3:

```bash
python -m aws_automation s3 list-buckets
python -m aws_automation s3 list-objects --bucket my-test-bucket
```

ECR:

```bash
python -m aws_automation ecr list-repositories
python -m aws_automation ecr list-images --repository my-application
```

Configuration and region override:

```bash
python -m aws_automation --config config/example.yaml --region eu-west-1 ec2 list
```

Verbose logging:

```bash
python -m aws_automation --verbose --profile my-profile ecr list-repositories
```

## Dry-run example

Mutating EC2 commands support a global `--dry-run` flag. In dry-run mode, the tool reports what would happen and does not call the AWS API operation.

```bash
python -m aws_automation --dry-run ec2 stop --instance-id i-0123456789abcdef0
```

Example output:

```text
DRY RUN: EC2 instance i-0123456789abcdef0 would be stopped.
No changes were made.
```

## Error handling

The tool returns clear non-zero failures for common cases such as:

- invalid command-line arguments
- missing configuration files
- invalid YAML configuration
- invalid AWS region or resource identifiers
- missing AWS credentials
- missing IAM permissions
- resource not found
- general AWS API or SDK failures

Expected user input errors are handled without showing Python tracebacks.

## Development notes

- Keep AWS interactions inside the service modules
- Reuse `create_session()` and `create_client()` instead of duplicating Boto3 setup
- Reuse validators instead of embedding regex checks in command handlers
- Service classes are designed for future pytest tests with mocked clients
- The `tests/` directory is intentionally minimal for now because the exercise focuses on implementation structure first
