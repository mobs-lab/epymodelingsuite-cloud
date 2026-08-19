"""Regression tests for the v2 workflow's staged rollout features."""

from pathlib import Path

import pytest

WORKFLOW_V2 = Path(__file__).resolve().parents[2] / "terraform" / "workflow-v2.yaml"


@pytest.fixture(scope="module")
def workflow_source() -> str:
    """Load the staging template once for source-level rendering checks."""
    return WORKFLOW_V2.read_text()


@pytest.fixture(scope="module")
def wait_job_source(workflow_source: str) -> str:
    """Isolate the waitJob subworkflow so assertions cannot match other stages."""
    return workflow_source.split("waitJob:\n", maxsplit=1)[1].split(
        "\n# ========== SUBWORKFLOW: Wait for Files", maxsplit=1
    )[0]


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_instances_are_selected_from_the_runtime_machine_type(workflow_source, stage):
    """Every stage must build its instance policy from the workflow input."""
    expression = (
        f'instances: $${{if(machineType{stage} == "", autoInstances, configuredInstances{stage})}}'
    )

    assert workflow_source.count(expression) == 1


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_configured_policy_uses_the_runtime_machine_and_hyperdisk(workflow_source, stage):
    """Every non-empty runtime selection must receive the Hyperdisk policy."""
    policy_start = workflow_source.index(f"- configuredInstances{stage}:")
    possible_ends = (
        workflow_source.find("\n          - configuredInstances", policy_start + 1),
        workflow_source.find("\n\n    #", policy_start + 1),
    )
    policy_end = min(end for end in possible_ends if end != -1)
    policy = workflow_source[policy_start:policy_end]

    assert f"machineType: $${{machineType{stage}}}" in policy
    assert "provisioningModel: STANDARD" in policy
    assert "type: hyperdisk-balanced" in policy
    assert "sizeGb: 50" in policy


def test_empty_machine_type_uses_an_unconstrained_policy(workflow_source):
    """Auto-selection must send an empty policy instead of an empty machine name."""
    assert "- autoInstances:\n              - policy: {}" in workflow_source


@pytest.mark.parametrize("stage", ["a", "b", "c"])
def test_instance_policy_has_no_apply_time_machine_branch(workflow_source, stage):
    """Terraform values may supply defaults but must not choose the Batch policy."""
    assert f'if stage_{stage}_machine_type != ""' not in workflow_source
    assert f'regexall("^c4d-", stage_{stage}_machine_type)' not in workflow_source


def _watchdog_stalls(
    *,
    running: int,
    assigned: int,
    succeeded: int,
    failed: int,
    expected_parallelism: int,
    task_count: int,
    flat_seconds: int,
    zero_fill_seconds: int,
) -> bool:
    """Evaluate the watchdog contract independently of Workflows syntax."""
    ever_started = running + assigned + succeeded + failed
    remaining = max(task_count - succeeded - failed, 0)
    target_slots = min(expected_parallelism, remaining)
    occupied = running + assigned
    filled = 1 if target_slots <= 0 else occupied / target_slots

    return (
        ever_started == 0
        and zero_fill_seconds >= 1500
        or ever_started > 0
        and filled < 0.5
        and flat_seconds >= 900
        or ever_started > 0
        and filled < 0.9
        and flat_seconds >= 5400
    )


@pytest.mark.parametrize(
    (
        "counts",
        "expected_parallelism",
        "task_count",
        "flat_seconds",
        "zero_fill_seconds",
        "expected",
    ),
    [
        ({"running": 2}, 10, 10, 900, 900, True),
        ({"running": 50}, 52, 52, 7200, 7200, False),
        ({}, 1, 1, 1500, 1500, True),
        ({"succeeded": 100}, 100, 200, 900, 900, True),
        ({"running": 1, "succeeded": 51}, 100, 52, 7200, 7200, False),
    ],
    ids=[
        "severe-partial-fill",
        "healthy-near-fill",
        "zero-fill",
        "empty-next-wave",
        "healthy-drain-down",
    ],
)
def test_watchdog_conformance_cases(
    counts,
    expected_parallelism,
    task_count,
    flat_seconds,
    zero_fill_seconds,
    expected,
):
    """The detector must match the five capacity scenarios in the design contract."""
    assert (
        _watchdog_stalls(
            running=counts.get("running", 0),
            assigned=counts.get("assigned", 0),
            succeeded=counts.get("succeeded", 0),
            failed=counts.get("failed", 0),
            expected_parallelism=expected_parallelism,
            task_count=task_count,
            flat_seconds=flat_seconds,
            zero_fill_seconds=zero_fill_seconds,
        )
        is expected
    )


def test_watchdog_measures_occupancy_against_remaining_demand(wait_job_source):
    """Completed work must reduce demand without being mistaken for occupied slots."""
    assert "- remaining: $${taskCount - cSucceeded - cFailed}" in wait_job_source
    assert (
        "- targetSlots: $${if(safeParallelism < remaining, safeParallelism, remaining)}"
        in wait_job_source
    )
    assert "- occupied: $${cRunning + cAssigned}" in wait_job_source
    assert "- filled: $${if(targetSlots <= 0, 1, occupied / targetSlots)}" in wait_job_source


def test_watchdog_defaults_missing_counts_without_using_pending(wait_job_source):
    """A job with an empty count map must still be recognized as zero-filled."""
    assert "- emptyCounts: {}" in wait_job_source
    assert (
        'default(map.get(j.body, ["status", "taskGroups", "group0", "counts"]), '
        "emptyCounts)" in wait_job_source
    )
    for state in ("RUNNING", "ASSIGNED", "SUCCEEDED", "FAILED"):
        assert f'int(default(map.get(lastCounts, "{state}"), 0))' in wait_job_source

    assert 'map.get(lastCounts, "PENDING")' not in wait_job_source


def test_watchdog_resets_the_timer_during_healthy_occupancy(wait_job_source):
    """A completed wave must receive a fresh grace period before the next wave fills."""
    assert "- flatPolls: $${if(filled >= 0.9 or madeProgress, 0, flatPolls + 1)}" in wait_job_source


def test_zero_fill_grace_outlasts_batch_vm_creation_window(wait_job_source):
    """Zero fill must wait past Batch's 1080-second hard-error reporting window."""
    assert "- zeroFillGraceSeconds: 1500" in wait_job_source
    assert "everStarted == 0 and zeroFillSeconds >= zeroFillGraceSeconds" in wait_job_source


def test_wait_bound_scales_with_task_waves(wait_job_source):
    """Serial and throttled jobs need one task-duration allowance per execution wave."""
    assert (
        "- waves: $${int((taskCount + safeParallelism - 1) / safeParallelism)}" in wait_job_source
    )
    assert (
        "- maxWaitSeconds: $${waves * maxRunDurationSeconds + provisioningMarginSeconds}"
        in wait_job_source
    )
    assert (
        "- maxPolls: $${int((maxWaitSeconds + pollSeconds - 1) / pollSeconds)}" in wait_job_source
    )
    assert "code: WAIT_TIMEOUT" in wait_job_source


@pytest.mark.parametrize(
    ("stage", "parallelism", "task_count", "duration"),
    [
        ("A", "1", "1", "stage_a_max_run_duration"),
        ("B", "$${parallelism}", "$${N}", "stage_b_max_run_duration"),
        ("C", "1", "1", "stage_c_max_run_duration"),
    ],
)
def test_each_stage_supplies_watchdog_demand_and_duration(
    workflow_source, stage, parallelism, task_count, duration
):
    """Every wait call must provide enough context for occupancy and timeout math."""
    call_start = workflow_source.index(f"- wait_for_stage{stage}_completion:")
    call_end = workflow_source.index(f"- ensure_stage{stage}_completed:", call_start)
    call = workflow_source[call_start:call_end]

    assert f"expectedParallelism: {parallelism}" in call
    assert f"taskCount: {task_count}" in call
    assert "stallSeconds: 900" in call
    assert f"maxRunDurationSeconds: ${{{duration}}}" in call
