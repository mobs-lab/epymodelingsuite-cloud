"""Regression tests for runtime machine selection in the v2 workflow."""

from pathlib import Path

import pytest

WORKFLOW_V2 = Path(__file__).resolve().parents[2] / "terraform" / "workflow-v2.yaml"


@pytest.fixture(scope="module")
def workflow_source() -> str:
    """Load the staging template once for source-level rendering checks."""
    return WORKFLOW_V2.read_text()


@pytest.mark.parametrize("stage", ["A", "B", "C"])
def test_instances_are_selected_from_the_runtime_machine_type(workflow_source, stage):
    """Every stage must build its instance policy from the workflow input."""
    expression = (
        f'instances: $${{if(machineType{stage} == "", '
        f"autoInstances, configuredInstances{stage})}}"
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
