"""Regression tests for the no-replacement regional Terraform migration."""

from pathlib import Path

import pytest


TERRAFORM_DIR = Path(__file__).parents[2] / "terraform"


@pytest.fixture
def network_source() -> str:
    """Return the regional network resource definitions."""
    return (TERRAFORM_DIR / "network.tf").read_text()


@pytest.fixture
def main_source() -> str:
    """Return the Terraform definitions that own registries and workflows."""
    return (TERRAFORM_DIR / "main.tf").read_text()


def test_regional_resources_iterate_over_one_configured_map(
    network_source: str, main_source: str
) -> None:
    """Every regional resource must use the shared batch_regions map."""
    assert network_source.count("for_each = var.batch_regions") == 3
    assert 'resource "google_artifact_registry_repository" "repo" {' in main_source
    repository_block = main_source.split(
        'resource "google_artifact_registry_repository" "repo" {', 1
    )[1].split("}\n", 1)[0]
    assert "for_each = var.batch_regions" in repository_block


@pytest.mark.parametrize(
    ("old_address", "new_address"),
    [
        (
            "google_compute_subnetwork.batch_subnet",
            'google_compute_subnetwork.batch_subnet["us-central1"]',
        ),
        (
            "google_compute_router.batch_router",
            'google_compute_router.batch_router["us-central1"]',
        ),
        (
            "google_compute_router_nat.batch_nat",
            'google_compute_router_nat.batch_nat["us-central1"]',
        ),
        (
            "google_artifact_registry_repository.repo",
            'google_artifact_registry_repository.repo["us-central1"]',
        ),
    ],
)
def test_existing_resources_have_declarative_state_moves(
    network_source: str,
    main_source: str,
    old_address: str,
    new_address: str,
) -> None:
    """Legacy central1 resources must move in state instead of being recreated."""
    combined_source = network_source + main_source
    assert f"from = {old_address}" in combined_source
    assert f"to   = {new_address}" in combined_source


def test_control_plane_region_keeps_legacy_network_names(network_source: str) -> None:
    """The existing central1 names must survive the for_each conversion unchanged."""
    assert 'each.key == var.region ? var.subnet_name :' in network_source
    assert 'each.key == var.region ? "${var.network_name}-router" :' in network_source
    assert 'each.key == var.region ? "${var.network_name}-nat" :' in network_source


def test_workflows_receive_region_maps_without_the_dead_subnet_name(
    main_source: str,
) -> None:
    """Terraform must prepare region inputs without retaining the unused subnet name."""
    assert main_source.count("subnet_self_links") == 2
    assert main_source.count("allowed_batch_regions") == 2
    assert main_source.count("default_batch_region") == 2
    assert "subnet_name              =" not in main_source
