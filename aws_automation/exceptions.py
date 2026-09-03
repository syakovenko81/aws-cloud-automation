"""Application-specific exceptions."""


class AppError(Exception):
    """Base class for expected application errors."""

    exit_code = 1

    def __init__(self, message: str, exit_code: int | None = None) -> None:
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class ConfigError(AppError):
    """Raised when the configuration file is invalid."""

    exit_code = 2


class ValidationError(AppError):
    """Raised when user input is invalid."""

    exit_code = 2


class AWSServiceError(AppError):
    """Raised when an AWS SDK or API operation fails."""

    exit_code = 4

