"""Opt-in acceptance test for the real GCP Batch submission transport."""

import os
import subprocess
import time
import uuid

import pytest

from epycloud.execution import SubmissionPlan, get_execution_backend

_DELETE_TIMEOUT_SECONDS = 180
_DELETE_POLL_SECONDS = 5


@pytest.mark.live_gcp
def test_gcp_batch_submission_smoke():
    """Submit a no-op job, wait for success, and delete the exact resource."""

    if os.getenv("EPYCLOUD_RUN_LIVE_GCP") != "1":
        pytest.skip("Set EPYCLOUD_RUN_LIVE_GCP=1 to create a real Batch job")

    project_id = os.getenv("EPYCLOUD_LIVE_GCP_PROJECT")
    image_uri = os.getenv("EPYCLOUD_LIVE_GCP_IMAGE_URI")
    region = os.getenv("EPYCLOUD_LIVE_GCP_REGION", "us-east5")
    service_account = os.getenv("EPYCLOUD_LIVE_GCP_SERVICE_ACCOUNT")
    if not project_id or not image_uri:
        pytest.fail(
            "Live GCP smoke test requires EPYCLOUD_LIVE_GCP_PROJECT and "
            "EPYCLOUD_LIVE_GCP_IMAGE_URI"
        )

    job_id = f"epycloud-smoke-{uuid.uuid4().hex[:12]}"
    job_name = f"projects/{project_id}/locations/{region}/jobs/{job_id}"
    allocation_policy = {}
    if service_account:
        allocation_policy["serviceAccount"] = {"email": service_account}

    payload = {
        "labels": {
            "component": "epycloud",
            "managed-by": "smoke-test",
        },
        "taskGroups": [
            {
                "taskCount": 1,
                "taskSpec": {
                    "runnables": [
                        {
                            "container": {
                                "imageUri": image_uri,
                                "entrypoint": "/bin/bash",
                                "commands": ["-c", "true"],
                            }
                        }
                    ],
                    "computeResource": {"cpuMilli": 1000, "memoryMib": 512},
                    "maxRunDuration": "300s",
                },
                "taskCountPerNode": 1,
            }
        ],
        "logsPolicy": {"destination": "CLOUD_LOGGING"},
    }
    if allocation_policy:
        payload["allocationPolicy"] = allocation_policy

    backend = get_execution_backend(
        {
            "execution": {"provider": "gcp"},
            "google_cloud": {"project_id": project_id, "region": region},
        }
    )
    plan = SubmissionPlan(
        provider="gcp",
        operation="job",
        target=job_name,
        payload=payload,
        display_details={"job_config": payload},
        metadata={"job_id": job_id},
    )

    submission_attempted = False
    try:
        submission_attempted = True
        ref = backend.submit_job(plan)
        assert ref.resource_name == job_name

        deadline = time.monotonic() + 900
        state = "UNKNOWN"
        while time.monotonic() < deadline:
            result = subprocess.run(
                [
                    "gcloud",
                    "batch",
                    "jobs",
                    "describe",
                    job_id,
                    f"--project={project_id}",
                    f"--location={region}",
                    "--format=value(status.state)",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                pytest.fail(f"Unable to describe live Batch job: {result.stderr.strip()}")
            state = result.stdout.strip()
            if state in {"SUCCEEDED", "FAILED"}:
                break
            time.sleep(15)

        assert state == "SUCCEEDED", f"Batch smoke job ended in state {state}"
    finally:
        if submission_attempted:
            _delete_job_and_wait(project_id, region, job_id, job_name)


def _delete_job_and_wait(project_id: str, region: str, job_id: str, job_name: str) -> None:
    """Delete an exact smoke-test job and wait until GCP reports NotFound."""

    cleanup = subprocess.run(
        [
            "gcloud",
            "batch",
            "jobs",
            "delete",
            job_id,
            f"--project={project_id}",
            f"--location={region}",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if cleanup.returncode != 0:
        if _is_not_found(cleanup):
            return
        pytest.fail(f"Failed to delete live Batch job {job_name}: {cleanup.stderr.strip()}")

    deadline = time.monotonic() + _DELETE_TIMEOUT_SECONDS
    last_state = "UNKNOWN"
    while time.monotonic() < deadline:
        described = subprocess.run(
            [
                "gcloud",
                "batch",
                "jobs",
                "describe",
                job_id,
                f"--project={project_id}",
                f"--location={region}",
                "--format=value(status.state)",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if described.returncode != 0:
            if _is_not_found(described):
                return
            pytest.fail(
                f"Unable to verify deletion of live Batch job {job_name}: "
                f"{described.stderr.strip()}"
            )
        last_state = described.stdout.strip() or "UNKNOWN"
        time.sleep(_DELETE_POLL_SECONDS)

    pytest.fail(
        f"Timed out waiting for live Batch job {job_name} to be deleted; "
        f"last state was {last_state}"
    )


def _is_not_found(result: subprocess.CompletedProcess[str]) -> bool:
    """Return whether a gcloud result represents an already-absent job."""

    output = f"{result.stdout}\n{result.stderr}".lower()
    return any(marker in output for marker in ("not_found", "not found", "does not exist"))


def test_delete_job_waits_until_not_found(monkeypatch):
    """Cleanup does not return while the Batch resource is still deleting."""

    responses = iter(
        [
            subprocess.CompletedProcess([], 0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                [], 0, stdout="DELETION_IN_PROGRESS\n", stderr=""
            ),
            subprocess.CompletedProcess(
                [], 1, stdout="", stderr="NOT_FOUND: Batch job was not found"
            ),
        ]
    )
    commands = []

    def fake_run(command, **_kwargs):
        commands.append(command)
        return next(responses)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    _delete_job_and_wait("project", "us-east5", "job-id", "job-name")

    assert [command[3] for command in commands] == ["delete", "describe", "describe"]
