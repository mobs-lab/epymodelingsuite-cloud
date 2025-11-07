"""Custom exceptions for epycloud CLI tool.

This module defines a hierarchy of custom exceptions for better error
categorization and handling throughout the application.
"""


class EpycloudError(Exception):
    """Base exception for all epycloud errors.

    Parameters
    ----------
    message : str
        Error message describing what went wrong.
    details : dict, optional
        Additional structured information about the error.

    Attributes
    ----------
    message : str
        The error message.
    details : dict
        Dictionary containing additional error context.
    """

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self):
        """Format error message with optional details.

        Returns
        -------
        str
            Formatted error message.
        """
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConfigError(EpycloudError):
    """Configuration loading or validation error.

    Raised when:
    - Configuration files are missing or invalid
    - Required configuration keys are missing
    - Configuration values are invalid
    - Configuration initialization fails
    """

    pass


class ValidationError(EpycloudError):
    """Input validation error.

    Raised when:
    - User-provided inputs fail validation
    - Path validation fails
    - Identifier format is invalid
    - Token format is invalid
    """

    pass


class CloudAPIError(EpycloudError):
    """Error communicating with Google Cloud APIs.

    Parameters
    ----------
    message : str
        Error message describing the API error.
    api : str, optional
        Name of the API that failed.
    status_code : int, optional
        HTTP status code from the API response.

    Attributes
    ----------
    api : str or None
        Name of the API that failed.
    status_code : int or None
        HTTP status code if available.
    """

    def __init__(self, message: str, api: str = None, status_code: int = None):
        details = {}
        if api:
            details["api"] = api
        if status_code:
            details["status_code"] = status_code

        super().__init__(message, details)
        self.api = api
        self.status_code = status_code


class ResourceNotFoundError(EpycloudError):
    """Requested resource not found.

    Raised when:
    - Cloud Workflows execution not found
    - Batch job not found
    - GCS bucket or object not found
    - Configuration profile not found
    """

    pass
