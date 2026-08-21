"""Tests for the Hyperdisk machine-family guard and the per-stage fallback chains."""

import pytest

from epycloud.commands.run.cloud.batch_config import build_batch_job_config
from epycloud.exceptions import ValidationError
from epycloud.execution.gcp_machines import (
    ARM_MACHINE_FAMILIES,
    HYPERDISK_MACHINE_FAMILIES,
    MACHINE_CHAINS_BY_REQUIREMENT,
    MACHINE_SPECS,
    STAGE_MACHINE_CHAINS,
    get_candidate_chain,
    get_machine_family,
    is_hyperdisk_family,
    validate_hyperdisk_family,
)


def test_guard_lives_with_the_gcp_backend_not_in_shared_validation():
    """Hyperdisk is GCP-only; lib/validation.py must not grow this coupling."""
    import epycloud.execution.gcp as gcp
    import epycloud.lib.validation as shared

    assert gcp.is_hyperdisk_family is is_hyperdisk_family
    assert gcp.validate_hyperdisk_family is validate_hyperdisk_family
    assert not hasattr(shared, "is_hyperdisk_family")


class TestIsHyperdiskFamily:
    """Every family the chains can contain must boot from hyperdisk-balanced."""

    @pytest.mark.parametrize(
        "machine_type",
        [
            "c3-standard-4",
            "c3d-standard-4",
            "c4-standard-2",
            "c4-standard-4",
            "c4d-standard-2",
            "c4d-standard-4",
            "n4-standard-2",
            "n4d-standard-2",
            "n4d-standard-4",
        ],
    )
    def test_accepts_hyperdisk_families(self, machine_type):
        assert is_hyperdisk_family(machine_type) is True

    @pytest.mark.parametrize(
        "machine_type",
        ["n2-standard-2", "n2d-standard-2", "e2-standard-2", "c2-standard-8", "t2d-standard-1"],
    )
    def test_rejects_persistent_disk_families(self, machine_type):
        assert is_hyperdisk_family(machine_type) is False

    @pytest.mark.parametrize("machine_type", ["c4a-standard-4", "n4a-standard-2"])
    def test_rejects_arm_families(self, machine_type):
        """Arm64 is Hyperdisk-capable but the image is amd64, so it is still out."""
        assert is_hyperdisk_family(machine_type) is False

    @pytest.mark.parametrize("machine_type", ["", "   ", "notamachinetype"])
    def test_handles_empty_and_malformed(self, machine_type):
        assert is_hyperdisk_family(machine_type) is False

    def test_is_case_insensitive(self):
        assert is_hyperdisk_family("C4D-STANDARD-2") is True

    def test_arm_families_are_disjoint_from_hyperdisk_set(self):
        assert not (ARM_MACHINE_FAMILIES & HYPERDISK_MACHINE_FAMILIES)


class TestGetMachineFamily:
    @pytest.mark.parametrize(
        "machine_type,expected",
        [
            ("c4d-standard-2", "c4d"),
            ("n4-highmem-8", "n4"),
            ("", ""),
            ("bogus", ""),
        ],
    )
    def test_extracts_prefix(self, machine_type, expected):
        assert get_machine_family(machine_type) == expected


class TestValidateHyperdiskFamily:
    def test_returns_valid_machine_type_unchanged(self):
        assert validate_hyperdisk_family("c4-standard-2", "Stage B") == "c4-standard-2"

    def test_empty_string_bypasses_the_guard(self):
        """Empty means auto-select; the guard must short-circuit before rejecting it."""
        assert validate_hyperdisk_family("", "Stage B") == ""

    def test_rejects_persistent_disk_family_with_consequence(self):
        with pytest.raises(ValidationError) as exc:
            validate_hyperdisk_family("n2-standard-2", "Stage B")

        message = str(exc.value)
        assert "Stage B machine type 'n2-standard-2' cannot be used." in message
        assert "hyperdisk-balanced" in message
        # The message must explain what goes wrong, or it reads as a spurious lint.
        assert "1080s" in message
        # ...and offer the stage's own chain as the way out.
        assert "c4d-standard-2, c4-standard-2, n4d-standard-2, n4-standard-2" in message

    def test_arm_family_gets_a_distinct_message(self):
        with pytest.raises(ValidationError) as exc:
            validate_hyperdisk_family("c4a-standard-4", "Stage C")

        message = str(exc.value)
        assert "Arm64" in message
        assert "amd64" in message
        assert "c4d-standard-4, c4-standard-4, n4d-standard-4, c3-standard-4" in message

    def test_unknown_stage_name_still_raises_without_a_suggestion(self):
        with pytest.raises(ValidationError) as exc:
            validate_hyperdisk_family("e2-standard-2", "Builder")

        assert "Use one of" not in str(exc.value)


class TestStageChains:
    """Fallback chains must preserve each stage's resource requirements."""

    def test_stage_a_and_b_share_the_standard_2_chain(self):
        expected = ("c4d-standard-2", "c4-standard-2", "n4d-standard-2", "n4-standard-2")
        assert STAGE_MACHINE_CHAINS["a"] == expected
        assert STAGE_MACHINE_CHAINS["b"] == expected

    def test_stage_c_chain_meets_its_4000_mcpu_minimum(self):
        assert STAGE_MACHINE_CHAINS["c"] == (
            "c4d-standard-4",
            "c4-standard-4",
            "n4d-standard-4",
            "c3-standard-4",
        )
        # 2 vCPU cannot satisfy Stage C's 4000 mCPU request.
        assert all(c.rsplit("-", 1)[-1] == "4" for c in STAGE_MACHINE_CHAINS["c"])

    def test_c4_is_the_first_equivalent_fallback(self):
        """C4 follows C4D where both machine types have identical resources."""
        assert MACHINE_CHAINS_BY_REQUIREMENT[(2000, 8192)][1] == "c4-standard-2"
        assert MACHINE_CHAINS_BY_REQUIREMENT[(4000, 16384)][1] == "c4-standard-4"

    def test_every_candidate_can_boot_hyperdisk(self):
        """A candidate that cannot boot the pipeline's disk is a guaranteed failure."""
        for requirement, chain in MACHINE_CHAINS_BY_REQUIREMENT.items():
            for candidate in chain:
                assert is_hyperdisk_family(candidate), f"{requirement}: {candidate}"

    def test_every_candidate_has_recorded_specs(self):
        """Requirement filtering needs local specs for every maintained candidate."""
        for chain in MACHINE_CHAINS_BY_REQUIREMENT.values():
            for candidate in chain:
                assert candidate in MACHINE_SPECS, candidate

    def test_memory_is_non_decreasing_along_every_chain(self):
        """Fallback must never lower memory, or a capacity failure becomes an OOM.

        This is what excludes c4-standard-8 (30720 MiB) from the standard-8
        chain, whose head c4d-standard-8 is 31744 MiB.
        """
        for requirement, chain in MACHINE_CHAINS_BY_REQUIREMENT.items():
            memories = [MACHINE_SPECS[c][1] for c in chain]
            assert memories == sorted(memories), f"{requirement}: {list(zip(chain, memories))}"

    def test_vcpu_is_constant_along_every_chain(self):
        """A maintained pool changes family, except for requirement-driven shape selection."""
        for requirement, chain in MACHINE_CHAINS_BY_REQUIREMENT.items():
            vcpus = {MACHINE_SPECS[c][0] for c in chain}
            assert len(vcpus) == 1, f"{requirement}: {vcpus}"

    def test_c4_standard_8_lowers_memory(self):
        """Regression guard for the plan's 'C4 is a spec-identical drop-in' claim.

        True at standard-2 and standard-4, false at standard-8.
        """
        assert MACHINE_SPECS["c4-standard-8"][1] < MACHINE_SPECS["c4d-standard-8"][1]

    def test_standard_8_chain_preserves_resources_and_excludes_c4(self):
        """The 8-vCPU chain must not include memory-lowering c4-standard-8."""
        assert MACHINE_CHAINS_BY_REQUIREMENT[(8000, 32768)] == (
            "c4d-standard-8",
            "c3-standard-8",
            "c3d-standard-8",
            "n4d-standard-8",
        )
        assert "c4-standard-8" not in MACHINE_CHAINS_BY_REQUIREMENT[(8000, 32768)]

    def test_highmem_4_chain_serves_a_memory_bound_stage_c(self):
        """Highmem-4 preserves memory while meeting Stage C's CPU minimum."""
        chain = MACHINE_CHAINS_BY_REQUIREMENT[(4000, 32768)]

        assert chain[0] == "c3-highmem-4"
        for candidate in chain:
            vcpu, mem = MACHINE_SPECS[candidate]
            assert vcpu == 4, candidate
            assert vcpu * 1000 >= 4000, candidate  # Stage C minimum
            assert mem >= MACHINE_SPECS["c4d-standard-8"][1], candidate


class TestGetCandidateChain:
    """Requirement lookup must prefer smaller shapes without lowering resources."""

    def test_standard_two_chain_serves_builder_and_runner(self):
        """The 2000 mCPU and 7168 MiB workload keeps the measured standard-2 order."""
        assert get_candidate_chain(2000, 7168) == (
            "c4d-standard-2",
            "c4-standard-2",
            "n4d-standard-2",
            "n4-standard-2",
        )

    def test_memory_bound_stage_prefers_highmem_four(self):
        """A 31744 MiB stage must use 4-vCPU highmem before any 8-vCPU shape."""
        assert get_candidate_chain(4000, 31744) == (
            "c3-highmem-4",
            "c3d-highmem-4",
            "n4d-highmem-4",
            "n4-highmem-4",
        )

    def test_eight_core_requirement_uses_standard_eight(self):
        """An actual 8000 mCPU minimum cannot be served by highmem-4."""
        assert get_candidate_chain(8000, 31744) == (
            "c4d-standard-8",
            "c3-standard-8",
            "c3d-standard-8",
            "n4d-standard-8",
        )

    def test_candidates_below_the_memory_minimum_are_filtered(self):
        """A pool may contain mixed memory sizes, so each member is checked."""
        assert get_candidate_chain(2000, 8192) == (
            "n4d-standard-2",
            "n4-standard-2",
        )

    def test_unsupported_requirement_has_no_implicit_downgrade(self):
        """An unknown larger workload must require an explicit safe configuration."""
        assert get_candidate_chain(16000, 65536) == ()


class TestBatchConfigBootDisk:
    """The Batch job document must attach the boot disk for every chain member."""

    def _instances(self, machine_type):
        config = build_batch_job_config(
            stage="B",
            exp_id="test",
            run_id="20260819-000000-abcdef12",
            task_index=0,
            num_tasks=None,
            output_config=None,
            image_uri="us-central1-docker.pkg.dev/p/r/i:tag",
            bucket_name="test-bucket",
            dir_prefix="pipeline/dev/flu/",
            github_forecast_repo="mobs-lab/forecast",
            project_id="test-project",
            cpu_milli=2000,
            memory_mib=7168,
            machine_type=machine_type,
            max_run_duration=36000,
            task_count_per_node=1,
            batch_sa_email="batch@p.iam.gserviceaccount.com",
        )
        return config["allocationPolicy"].get("instances")

    @pytest.mark.parametrize("machine_type", ["c4d-standard-2", "c4-standard-2", "n4-standard-2"])
    def test_hyperdisk_families_get_a_boot_disk(self, machine_type):
        policy = self._instances(machine_type)[0]["policy"]

        assert policy["machineType"] == machine_type
        assert policy["bootDisk"] == {"type": "hyperdisk-balanced", "sizeGb": 50}

    def test_c4_is_no_longer_treated_as_persistent_disk(self):
        """Regression: the old startswith("c4d-") gate left C4 without a boot disk."""
        assert "bootDisk" in self._instances("c4-standard-2")[0]["policy"]

    def test_empty_machine_type_leaves_allocation_to_google(self):
        assert self._instances("") is None
