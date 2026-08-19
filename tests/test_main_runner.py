"""Tests for Stage B completion markers and resume behavior."""

import sys
from hashlib import sha256
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

dispatcher_module = ModuleType("epymodelingsuite.dispatcher")
dispatcher_module.dispatch_runner = MagicMock()
telemetry_module = ModuleType("epymodelingsuite.telemetry")
telemetry_module.ExecutionTelemetry = MagicMock()

with patch.dict(
    sys.modules,
    {
        "epymodelingsuite.dispatcher": dispatcher_module,
        "epymodelingsuite.telemetry": telemetry_module,
    },
):
    import main_runner


def _path(*parts: str) -> str:
    return "/".join(parts)


@pytest.fixture
def runner_mocks(monkeypatch):
    """Install the common runner environment and external boundary mocks."""
    monkeypatch.setenv("TASK_INDEX", "3")
    monkeypatch.setenv("SKIP_EXISTING", "true")

    logger = MagicMock()
    telemetry = MagicMock()
    telemetry_type = MagicMock()
    telemetry_type.return_value.__enter__.return_value = telemetry

    with (
        patch.object(
            main_runner.storage,
            "get_config",
            return_value={
                "mode": "local",
                "exp_id": "test-exp",
                "run_id": "test-run",
                "dir_prefix": "pipeline/test",
                "bucket": "",
            },
        ),
        patch.object(main_runner.storage, "get_path", side_effect=_path),
        patch.object(main_runner.storage, "load_bytes", return_value=b"input bytes"),
        patch.object(main_runner.storage, "save_bytes") as save_bytes,
        patch.object(main_runner.storage, "save_json") as save_json,
        patch.object(main_runner.storage, "save_telemetry_summary") as save_telemetry,
        patch.object(main_runner, "ExecutionTelemetry", telemetry_type),
        patch.object(main_runner, "dispatch_runner", return_value="result") as dispatch,
        patch.object(main_runner, "setup_logger", return_value=logger),
        patch.object(main_runner, "handle_stage_error") as handle_error,
    ):
        yield {
            "dispatch": dispatch,
            "handle_error": handle_error,
            "logger": logger,
            "save_bytes": save_bytes,
            "save_json": save_json,
            "save_telemetry": save_telemetry,
        }


@pytest.mark.unit
def test_matching_marker_skips_deserialization_and_execution(runner_mocks):
    """A matching digest proves the saved result is reusable.

    Resume must return before deserializing the workload, dispatching the
    simulation, or writing replacement artifacts.
    """
    digest = sha256(b"input bytes").hexdigest()

    with (
        patch.object(main_runner.storage, "exists", return_value=True),
        patch.object(main_runner.storage, "load_json", return_value={"input_digest": digest}),
        patch.object(main_runner.dill, "loads") as loads,
    ):
        main_runner.main()

    loads.assert_not_called()
    runner_mocks["dispatch"].assert_not_called()
    runner_mocks["save_bytes"].assert_not_called()
    runner_mocks["save_json"].assert_not_called()
    runner_mocks["handle_error"].assert_not_called()


@pytest.mark.unit
def test_changed_input_digest_recomputes_and_replaces_marker(runner_mocks):
    """Changed builder input invalidates an otherwise complete result.

    The runner must execute the new workload and publish a marker containing
    the new input digest so later retries can safely resume.
    """
    with (
        patch.object(main_runner.storage, "exists", return_value=True),
        patch.object(main_runner.storage, "load_json", return_value={"input_digest": "old"}),
        patch.object(main_runner.dill, "loads", return_value="workload"),
        patch.object(main_runner.dill, "dumps", return_value=b"result bytes"),
    ):
        main_runner.main()

    runner_mocks["dispatch"].assert_called_once_with("workload")
    marker_path, marker = runner_mocks["save_json"].call_args.args
    assert marker_path.endswith("runner-artifacts/result_00003.done.json")
    assert marker["input_digest"] == sha256(b"input bytes").hexdigest()
    assert marker["completed_at"].endswith("+00:00")
    runner_mocks["handle_error"].assert_not_called()


@pytest.mark.unit
def test_result_without_marker_recomputes(runner_mocks):
    """A result without its completion marker is never trusted.

    This covers results created before markers existed and interrupted writes
    that did not reach the final marker publication step.
    """
    with (
        patch.object(main_runner.storage, "exists", return_value=False) as exists,
        patch.object(main_runner.storage, "load_json") as load_json,
        patch.object(main_runner.dill, "loads", return_value="workload"),
        patch.object(main_runner.dill, "dumps", return_value=b"result bytes"),
    ):
        main_runner.main()

    assert exists.call_count == 1
    load_json.assert_not_called()
    runner_mocks["dispatch"].assert_called_once_with("workload")
    runner_mocks["save_json"].assert_called_once()


@pytest.mark.unit
def test_false_string_disables_resume(runner_mocks, monkeypatch):
    """The literal string ``false`` must parse as false.

    Treating every non-empty environment value as true would make ``--fresh``
    silently resume instead of recomputing the task.
    """
    monkeypatch.setenv("SKIP_EXISTING", "false")

    with (
        patch.object(main_runner.storage, "exists") as exists,
        patch.object(main_runner.dill, "loads", return_value="workload"),
        patch.object(main_runner.dill, "dumps", return_value=b"result bytes"),
    ):
        main_runner.main()

    exists.assert_not_called()
    runner_mocks["dispatch"].assert_called_once_with("workload")
    runner_mocks["save_json"].assert_called_once()
