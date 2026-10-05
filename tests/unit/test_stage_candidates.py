"""Tests for resolving stage fallback candidates and explicit pin state."""

from unittest.mock import patch

import pytest

from epycloud.commands.run.validation import resolve_stage_candidates


def resolve(stage_config, override=None):
    """Resolve a Stage C config with stable project and default requirements."""
    return resolve_stage_candidates(
        stage_config,
        override,
        "Stage C",
        "test-project",
        "us-central1",
        default_cpu_milli=4000,
        default_memory_mib=15360,
        default_max_run_duration=7200,
    )


@pytest.mark.parametrize(
    "machine_types",
    [[], "c4d-standard-4", [""], ["c4d-standard-4", "c4d-standard-4"]],
)
def test_invalid_candidate_shapes_are_rejected(machine_types):
    """Empty, scalar, blank, and duplicate chains cannot safely enter the workflow loop."""
    assert resolve({"machine_types": machine_types}) is None


def test_non_mapping_stage_config_is_rejected():
    """A malformed stage block must return a validation error instead of crashing."""
    assert resolve(["c4d-standard-4"]) is None


def test_empty_cli_override_is_rejected_instead_of_becoming_pinned_auto_select():
    """An explicitly supplied pin must name a real machine candidate."""
    assert resolve({}, override="  ") is None


@patch("epycloud.commands.run.validation.validate_and_get_machine_specs")
def test_each_candidate_keeps_its_own_resolved_resources(mock_specs):
    """The workflow must not reuse the head candidate's CPU and memory for replacements."""
    mock_specs.side_effect = [(4000, 15360), (4000, 16384)]

    candidates, pinned = resolve(
        {
            "cpu_milli": 4000,
            "memory_mib": 15360,
            "machine_types": ["c4d-standard-4", "n4d-standard-4"],
        }
    )

    assert pinned is False
    assert [(item.machine_type, item.cpu_milli, item.memory_mib) for item in candidates] == [
        ("c4d-standard-4", 4000, 15360),
        ("n4d-standard-4", 4000, 16384),
    ]
    assert mock_specs.call_count == 2


@patch("epycloud.commands.run.validation.validate_and_get_machine_specs")
def test_cli_override_is_one_pinned_candidate(mock_specs):
    """An explicit CLI machine type disables fallback regardless of configured chains."""
    mock_specs.return_value = (8000, 32768)

    candidates, pinned = resolve(
        {"machine_types": ["c4d-standard-4", "c4-standard-4"]},
        override="n4d-standard-8",
    )

    assert pinned is True
    assert [item.machine_type for item in candidates] == ["n4d-standard-8"]
    mock_specs.assert_called_once_with("n4d-standard-8", "Stage C", "test-project", "us-central1")


@patch("epycloud.commands.run.validation.validate_and_get_machine_specs")
def test_legacy_scalar_stays_one_unpinned_compatibility_candidate(mock_specs):
    """Older configs remain runnable but do not masquerade as an explicit CLI pin."""
    mock_specs.return_value = (4000, 15360)

    candidates, pinned = resolve({"machine_type": "c4d-standard-4"})

    assert pinned is False
    assert [item.machine_type for item in candidates] == ["c4d-standard-4"]


def test_empty_legacy_scalar_preserves_google_auto_selection():
    """An empty legacy scalar becomes one auto-select candidate without a GCP lookup."""
    candidates, pinned = resolve({"machine_type": ""})

    assert pinned is False
    assert len(candidates) == 1
    assert candidates[0].machine_type == ""
    assert candidates[0].cpu_milli == 4000
    assert candidates[0].memory_mib == 15360


@pytest.mark.parametrize(
    ("specs", "minimum_field"),
    [((2000, 32768), "mCPU"), ((4000, 8192), "MiB")],
)
@patch("epycloud.commands.run.validation.validate_and_get_machine_specs")
def test_candidate_below_a_stage_minimum_is_rejected(mock_specs, specs, minimum_field, capsys):
    """Every candidate must satisfy both minima, including the first attempt."""
    mock_specs.return_value = specs

    assert resolve({"machine_types": ["undersized-machine"]}) is None
    assert minimum_field in capsys.readouterr().err


@patch("epycloud.commands.run.validation.validate_and_get_machine_specs")
def test_memory_decrease_is_rejected_even_when_both_candidates_meet_the_minimum(mock_specs):
    """Fallback must not turn a capacity failure into an avoidable memory downgrade."""
    mock_specs.side_effect = [(4000, 32768), (8000, 31744)]

    assert (
        resolve(
            {
                "cpu_milli": 4000,
                "memory_mib": 15360,
                "machine_types": ["larger-memory", "smaller-memory"],
            }
        )
        is None
    )


@patch("epycloud.commands.run.validation.warning")
@patch("epycloud.commands.run.validation.validate_and_get_machine_specs")
def test_plural_key_wins_and_names_the_ignored_legacy_key(mock_specs, mock_warning):
    """Mixed old and new config must be deterministic and visible to the operator."""
    mock_specs.return_value = (4000, 15360)

    candidates, _ = resolve(
        {
            "machine_types": ["c4-standard-4"],
            "machine_type": "c4d-standard-4",
        }
    )

    assert [item.machine_type for item in candidates] == ["c4-standard-4"]
    mock_warning.assert_called_once()
    assert "legacy machine_type" in mock_warning.call_args.args[0]
