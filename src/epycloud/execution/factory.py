"""Execution backend selection."""

from collections.abc import Callable
from subprocess import CompletedProcess
from typing import Any

from epycloud.exceptions import ConfigError

from .base import ExecutionBackend

SUPPORTED_EXECUTION_PROVIDERS = frozenset({"gcp"})


def get_execution_provider(config: dict[str, Any]) -> str:
    """Return and validate the configured execution provider.

    Configurations created before the provider layer default to GCP.
    """

    if "execution" not in config:
        return "gcp"
    execution = config["execution"]
    if not isinstance(execution, dict):
        raise ConfigError("execution must be a mapping")

    raw_provider = execution.get("provider", "gcp")
    if not isinstance(raw_provider, str) or not raw_provider.strip():
        raise ConfigError("execution.provider must be a non-empty string")

    provider = raw_provider.strip().lower()
    if provider not in SUPPORTED_EXECUTION_PROVIDERS:
        raise ConfigError(f"Unsupported execution provider: {provider}")
    return provider


def get_execution_backend(
    config: dict[str, Any],
    *,
    verbose: bool = False,
    command_runner: Callable[..., CompletedProcess[str]] | None = None,
    token_provider: Callable[[], str] | None = None,
    http_post: Callable[..., Any] | None = None,
    workflow_api: Any | None = None,
) -> ExecutionBackend:
    """Build the configured cloud execution backend.

    Configurations created before the provider layer default to GCP.
    """

    provider = get_execution_provider(config)

    if provider == "gcp":
        from .gcp import GcpExecutionBackend

        return GcpExecutionBackend(
            config,
            verbose=verbose,
            command_runner=command_runner,
            token_provider=token_provider,
            http_post=http_post,
            workflow_api=workflow_api,
        )

    raise AssertionError(f"No backend registered for validated provider: {provider}")
