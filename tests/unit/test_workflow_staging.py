"""Regression tests for the staging workflow's staged rollout features."""

import json
import re
from pathlib import Path

import pytest

WORKFLOW_STAGING = Path(__file__).resolve().parents[2] / "terraform" / "workflow-staging.yaml"
WORKFLOW_STAGING_SUBWORKFLOWS = (
    Path(__file__).resolve().parents[2] / "terraform" / "workflow-staging-subworkflows.yaml"
)
TERRAFORM_MAIN = Path(__file__).resolve().parents[2] / "terraform" / "main.tf"


@pytest.fixture(scope="module")
def workflow_source() -> str:
    """Assemble the staging templates for source-level rendering checks."""
    return "\n".join(
        [WORKFLOW_STAGING.read_text(), WORKFLOW_STAGING_SUBWORKFLOWS.read_text()]
    )


@pytest.fixture(scope="module")
def wait_job_source(workflow_source: str) -> str:
    """Isolate the waitJob subworkflow so assertions cannot match other stages."""
    return workflow_source.split("waitJob:\n", maxsplit=1)[1].split(
        "\n# ========== SUBWORKFLOW: Cancel and Drain", maxsplit=1
    )[0]


@pytest.fixture(scope="module")
def candidate_finalizer_source(workflow_source: str) -> str:
    """Isolate the shared candidate finalizer from the other subworkflows."""
    return workflow_source.split("waitAndFinalizeCandidate:\n", maxsplit=1)[1].split(
        "\n# ========== SUBWORKFLOW: Wait for Files", maxsplit=1
    )[0]


@pytest.fixture(scope="module")
def terraform_main_source() -> str:
    """Load the Terraform resources used by the staging workflow."""
    return TERRAFORM_MAIN.read_text()


def test_terraform_assembles_the_two_v2_templates(terraform_main_source):
    """Deployment must append the top-level subworkflows to the staging main body."""
    assert 'source_contents = join("\\n", [' in terraform_main_source
    assert 'templatefile("${path.module}/workflow-staging.yaml", {' in terraform_main_source
    assert (
        'templatefile("${path.module}/workflow-staging-subworkflows.yaml", {})'
        in terraform_main_source
    )


def test_batch_location_defaults_to_the_control_plane_region(workflow_source):
    """Legacy submissions must continue creating Batch jobs in the default region."""
    assert '- defaultBatchLocation: "${default_batch_region}"' in workflow_source
    assert (
        '- batchLocation: $${default(map.get(input, "batchLocation"), '
        "defaultBatchLocation)}" in workflow_source
    )


def test_run_output_stage_accepts_an_execution_override(workflow_source):
    """A submission must be able to disable Stage C without redeploying Terraform."""
    assert "- defaultRunOutputStage: ${run_output_stage}" in workflow_source
    assert (
        '- runOutputStage: $${default(map.get(input, "runOutputStage"), '
        "defaultRunOutputStage)}" in workflow_source
    )


def test_batch_location_rejects_regions_outside_the_terraform_allowlist(
    workflow_source,
):
    """A direct workflow input cannot escape the provisioned region set."""
    assert "- allowedBatchRegions: ${allowed_batch_regions}" in workflow_source
    assert "condition: $${not(batchLocation in allowedBatchRegions)}" in workflow_source
    assert 'code: "UNKNOWN_BATCH_REGION"' in workflow_source
    assert "raise: $${unknownBatchRegionError}" in workflow_source


def test_batch_location_drives_every_regional_job_surface(workflow_source):
    """Batch placement, image lookup, image URI, and subnet must select one region."""
    assert workflow_source.count('"/locations/" + batchLocation + "/jobs"') == 3
    assert workflow_source.count('"/locations/" + batchLocation + "/repositories/') == 3
    assert workflow_source.count('$${"regions/" + batchLocation}') == 3
    assert (
        '- repoUri: $${batchLocation + "-docker.pkg.dev/" + project + '
        '"/${repo_name}/${image_name}"}' in workflow_source
    )
    assert "- subnetSelfLinks: ${subnet_self_links}" in workflow_source
    assert "- subnetSelfLink: $${map.get(subnetSelfLinks, batchLocation)}" in workflow_source


def test_control_plane_location_no_longer_selects_batch_resources(workflow_source):
    """The workflow deployment region must not leak into data-plane placement."""
    assert '"/locations/" + location + "/jobs"' not in workflow_source
    assert '"/locations/" + location + "/repositories/' not in workflow_source
    assert '$${"regions/" + location}' not in workflow_source


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_instances_are_selected_from_the_runtime_machine_type(workflow_source, stage):
    """Every stage must use the instance policy built for its current candidate."""
    expression = f"instances: $${{candidateInstances{stage}}}"

    assert workflow_source.count(expression) == 1


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_configured_policy_uses_the_runtime_machine_and_hyperdisk(workflow_source, stage):
    """Every non-empty candidate must receive the Hyperdisk policy."""
    policy_start = workflow_source.index(f"- configuredCandidateInstances{stage}:")
    policy_end = workflow_source.index(f"- candidateInstances{stage}:", policy_start)
    policy = workflow_source[policy_start:policy_end]

    assert f"machineType: $${{candidateMachineType{stage}}}" in policy
    assert "provisioningModel: STANDARD" in policy
    assert "type: hyperdisk-balanced" in policy
    assert "sizeGb: 50" in policy


def test_empty_machine_type_uses_an_unconstrained_policy(workflow_source):
    """Auto-selection must send an empty policy instead of an empty machine name."""
    assert "- autoInstances:\n              - policy: {}" in workflow_source


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_legacy_submission_gets_one_default_candidate(workflow_source, stage):
    """A client without candidate arrays must preserve its resolved stage resources."""
    assert (
        f'- candidates{stage}: $${{default(map.get(input, "stage{stage}Candidates"),'
        in workflow_source
    )
    default_start = workflow_source.index(f"- defaultCandidates{stage}:")
    default_end = workflow_source.index("\n          -", default_start + 1)
    candidate = workflow_source[default_start:default_end]

    assert f"machine_type: $${{machineType{stage}}}" in candidate
    assert f"cpu_milli: $${{cpuMilli{stage}}}" in candidate
    assert f"memory_mib: $${{memoryMib{stage}}}" in candidate


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
    assert "- fillDenominator: $${if(targetSlots > 0, targetSlots, 1)}" in wait_job_source
    assert "- occupied: $${cRunning + cAssigned}" in wait_job_source
    assert (
        "- filled: $${if(targetSlots <= 0, 1, occupied / fillDenominator)}"
        in wait_job_source
    )


def test_completed_job_never_divides_by_zero(wait_job_source):
    """Eager expression evaluation must remain safe when remaining demand is zero."""
    assert "occupied / targetSlots" not in wait_job_source
    assert "occupied / fillDenominator" in wait_job_source


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


def test_zero_fill_grace_outlasts_batch_vm_creation_window(
    workflow_source, wait_job_source
):
    """Zero fill must wait past Batch's 1080-second hard-error reporting window."""
    assert (
        '- watchdogZeroFillGraceSeconds: $${int(default(map.get(input, '
        '"watchdogZeroFillGraceSeconds"), 1500))}' in workflow_source
    )
    assert "everStarted == 0 and zeroFillSeconds >= zeroFillGraceSeconds" in wait_job_source


def test_watchdog_timings_allow_bounded_staging_overrides(workflow_source):
    """Direct staging runs may shorten timers without changing normal defaults."""
    assert (
        '- watchdogStallSeconds: $${int(default(map.get(input, '
        '"watchdogStallSeconds"), 900))}' in workflow_source
    )
    assert (
        "watchdogStallSeconds < 15 or watchdogZeroFillGraceSeconds < 15"
        in workflow_source
    )


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
    assert '- outcome: "WAIT_TIMEOUT"' in wait_job_source


def test_wait_job_distinguishes_child_cancellation_from_failure(wait_job_source):
    """An externally cancelled child must not look eligible for fallback."""
    assert 'currentState in ["CANCELLED", "DELETION_IN_PROGRESS"]' in wait_job_source
    assert '- outcome: "CHILD_JOB_CANCELLED"' in wait_job_source
    assert 'condition: $${currentState == "FAILED"}' in wait_job_source


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
    """Every finalizer call must provide context for occupancy and timeout math."""
    call_start = workflow_source.index(f"- finalize_stage{stage}_candidate:")
    call_end = workflow_source.index(f"- accept_finalized_stage{stage}:", call_start)
    call = workflow_source[call_start:call_end]

    assert "call: waitAndFinalizeCandidate" in call
    assert f"expectedParallelism: {parallelism}" in call
    assert f"taskCount: {task_count}" in call
    assert "stallSeconds: $${watchdogStallSeconds}" in call
    assert "zeroFillGraceSeconds: $${watchdogZeroFillGraceSeconds}" in call
    assert f"maxRunDurationSeconds: ${{{duration}}}" in call


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_each_stage_iterates_suffixed_candidates(workflow_source, stage):
    """Every attempt must have a stable candidate index in its Batch job ID."""
    assert f"- run_stage{stage}_candidates:" in workflow_source
    assert f"in: $${{candidates{stage}}}" in workflow_source
    assert (
        f'jobId: $${{"stage-{stage.lower()}-" + uniqueId + "-" + string(ci{stage})}}'
        in workflow_source
    )


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_each_candidate_has_discovery_and_attribution_labels(workflow_source, stage):
    """Job and VM labels must identify the execution and selected candidate."""
    stage_start = workflow_source.index(f"- run_stage{stage}_candidates:")
    stage_end = workflow_source.find("# ========== STAGE", stage_start + 1)
    stage_source = workflow_source[stage_start : stage_end if stage_end != -1 else None]

    assert stage_source.count("execution_id: $${executionIdShort}") == 2
    assert stage_source.count(f"candidate_index: $${{string(ci{stage})}}") == 2
    assert stage_source.count(f"machine_type: $${{machineLabel{stage}}}") == 2
    assert stage_source.count(f"machine_selection: $${{machineSelection{stage}}}") == 2


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_each_candidate_resolves_records_and_pins_its_image(workflow_source, stage):
    """Resolve and record every attempt before submitting its digest-pinned job."""
    stage_start = workflow_source.index(f"- run_stage{stage}_candidates:")
    stage_end = workflow_source.find("# ========== STAGE", stage_start + 1)
    stage_source = workflow_source[stage_start : stage_end if stage_end != -1 else None]

    resolve_at = stage_source.index(f"- resolve_stage{stage}_image:")
    record_at = stage_source.index(f"- record_stage{stage}_image:")
    create_at = stage_source.index(f"- create_stage{stage}_job:")

    assert resolve_at < record_at < create_at
    assert "https://artifactregistry.googleapis.com/v1/projects/" in stage_source
    assert f"imageUri: $${{resolvedImage{stage}.uri}}" in stage_source
    assert f"IMAGE_DIGEST: $${{resolvedImage{stage}.digest}}" in stage_source
    assert stage_source.count(f"image_digest: $${{resolvedImage{stage}.short_digest}}") == 2
    assert (
        f'"run-metadata/image-provenance/stage-{stage.lower()}-candidate-"'
        in stage_source
    )


def test_image_resolver_returns_a_validated_full_and_short_digest(workflow_source):
    """The resolver must reject malformed versions and build an immutable image URI."""
    resolver = workflow_source.split("resolveImage:\n", maxsplit=1)[1].split(
        "\n# ========== SUBWORKFLOW: Persist Image Provenance", maxsplit=1
    )[0]

    assert "scopes: https://www.googleapis.com/auth/cloud-platform.read-only" in resolver
    assert 'len(digest) != 71 or text.substring(digest, 0, 7) != "sha256:"' in resolver
    assert "short_digest: $${text.substring(digest, 7, 19)}" in resolver
    assert 'uri: $${repoUri + "@" + digest}' in resolver


def test_full_digest_is_written_to_per_candidate_run_metadata(workflow_source):
    """GCS provenance must retain the full digest that cannot fit in a label."""
    recorder = workflow_source.split("recordImageProvenance:\n", maxsplit=1)[1].split(
        "\n# ========== SUBWORKFLOW: Wait for Batch", maxsplit=1
    )[0]

    assert "uploadType: media" in recorder
    assert "name: $${objectName}" in recorder
    assert "image_digest: $${resolvedImage.digest}" in recorder
    assert "image_uri: $${resolvedImage.uri}" in recorder
    assert "candidate_index: $${candidateIndex}" in recorder


def test_workflow_has_the_permissions_needed_for_image_provenance(
    terraform_main_source,
):
    """Grant Artifact Registry read and GCS object create without write roles."""
    assert (
        'resource "google_project_iam_member" "wf_artifact_registry_reader"'
        in terraform_main_source
    )
    assert 'role    = "roles/artifactregistry.reader"' in terraform_main_source
    assert (
        'resource "google_storage_bucket_iam_member" "wf_bucket_create"'
        in terraform_main_source
    )
    assert 'role   = "roles/storage.objectCreator"' in terraform_main_source


def test_stage_b_reuses_only_completed_results_after_failover(workflow_source):
    """Only replacement candidates should skip digest-matching completed tasks."""
    assert 'SKIP_EXISTING: $${if(ciB > 0, "true", "false")}' in workflow_source


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_each_stage_uses_the_shared_candidate_finalizer(workflow_source, stage):
    """All stages must share one success, cancellation, and exhaustion path."""
    stage_start = workflow_source.index(f"- run_stage{stage}_candidates:")
    finalize_at = workflow_source.index(f"- finalize_stage{stage}_candidate:", stage_start)
    accept_at = workflow_source.index(f"- accept_finalized_stage{stage}:", finalize_at)
    stage_end = workflow_source.find("# ========== STAGE", accept_at)
    call_source = workflow_source[finalize_at:accept_at]
    accept_source = workflow_source[accept_at : stage_end if stage_end != -1 else None]

    assert "call: waitAndFinalizeCandidate" in call_source
    assert f"stage: {stage}" in call_source
    assert f"candidateIndex: $${{ci{stage}}}" in call_source
    assert f"numCandidates: $${{numCandidates{stage}}}" in call_source
    assert f"result: candidateSucceeded{stage}" in call_source
    assert f"condition: $${{candidateSucceeded{stage}}}" in accept_source
    assert f"stage{stage}JobName: $${{job{stage}.body.name}}" in accept_source
    assert "next: break" in accept_source



def test_stage_b_packs_each_candidate_by_its_own_task_count(workflow_source):
    """Stage B uses each candidate's task count per node, capped at the number of tasks."""
    select_source = workflow_source.split("- select_stageB_candidate:", maxsplit=1)[1].split(
        "- resolve_stageB_image:", maxsplit=1
    )[0]

    assert (
        'default(map.get(candidateB, "task_count_per_node"), taskCountPerNode)'
        in select_source
    )
    assert (
        "if(candidateTaskCountPerNodeB > N, N, candidateTaskCountPerNodeB)"
        in select_source
    )
    assert "taskCountPerNode: $${candidateTaskCountPerNodeB}" in workflow_source
    assert "taskCountPerNode: $${taskCountPerNode}" not in workflow_source

def test_child_cancellation_stops_before_candidate_fallback(candidate_finalizer_source):
    """Manual child cancellation must raise before cancellation or replacement."""
    stop_at = candidate_finalizer_source.index("- stop_on_cancelled_child:")
    cancel_at = candidate_finalizer_source.index("- cancel_unsuccessful_candidate:")
    stop_source = candidate_finalizer_source[stop_at:cancel_at]

    assert stop_at < cancel_at
    assert 'condition: $${waitResult.outcome == "CHILD_JOB_CANCELLED"}' in stop_source
    assert "code: CHILD_JOB_CANCELLED" in stop_source
    assert "stage: $${stage}" in stop_source
    assert "raise: $${childCancelled}" in stop_source


def test_task_exit_code_failure_stops_before_candidate_fallback(candidate_finalizer_source):
    """An application exit code must raise instead of retrying on another machine."""
    stop_at = candidate_finalizer_source.index("- stop_on_task_failure:")
    cancel_at = candidate_finalizer_source.index("- cancel_unsuccessful_candidate:")
    stop_source = candidate_finalizer_source[stop_at:cancel_at]

    assert stop_at < cancel_at
    assert 'condition: $${waitResult.outcome == "FAILED"}' in stop_source
    assert "code: TASK_FAILED" in stop_source
    assert "raise: $${taskFailure}" in stop_source

    # The Workflows string literal escapes the backslash, so unescape it once.
    pattern = re.search(r'"(with exit code [^"]+)"\)\}', stop_source).group(1)
    pattern = pattern.replace("\\\\", "\\")
    event = (
        'Job failed due to task failure. Specifically, task with index 0 failed due '
        'to the following task event: "Task state is updated from RUNNING to FAILED '
        'on zones/us-central1-c/instances/1 with exit code {}."'
    )
    events = json.dumps([{"description": event.format(1)}])
    assert re.search(pattern, events)
    assert re.search(pattern, event.format(137))
    assert not re.search(pattern, event.format(50001))
    assert not re.search(pattern, "Job state is set from RUNNING to FAILED.")


def test_failed_candidate_is_drained_before_exhaustion(candidate_finalizer_source):
    """The final attempt must be drained before the workflow reports exhaustion."""
    cancel_at = candidate_finalizer_source.index("- cancel_unsuccessful_candidate:")
    exhaust_at = candidate_finalizer_source.index("- raise_if_candidates_exhausted:")

    assert cancel_at < exhaust_at
    assert "call: cancelJob" in candidate_finalizer_source[cancel_at:exhaust_at]


def test_candidate_finalizer_returns_whether_the_loop_should_stop(
    candidate_finalizer_source,
):
    """Success exits the stage loop while a drained nonfinal failure continues it."""
    assert candidate_finalizer_source.count("return: true") == 2
    assert "- continue_to_next_candidate:\n        return: false" in candidate_finalizer_source


def test_cancel_job_drains_before_returning(workflow_source):
    """A replacement must wait until the previous job reaches a terminal state."""
    cancel_source = workflow_source.split("cancelJob:\n", maxsplit=1)[1].split(
        "\n# ========== SUBWORKFLOW: Wait for Files", maxsplit=1
    )[0]

    assert 'lastState in ["CANCELLED", "SUCCEEDED", "FAILED"]' in cancel_source
    assert "range: $${[1, 40]}" in cancel_source
    assert "code: CANCEL_DRAIN_TIMEOUT" in cancel_source
    assert '"DELETION_IN_PROGRESS"' not in cancel_source
