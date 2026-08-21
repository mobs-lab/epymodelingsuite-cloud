"""Machine-family constraints for the Google Cloud execution backend.

Deliberately kept out of ``lib/validation.py``: Hyperdisk is a Google Cloud
compute concept that does not survive to a second provider backend, so it
belongs with the GCP backend rather than in a module that presents as shared.

Split out of ``gcp.py`` only to keep the import graph acyclic:
``gcp.py`` imports ``commands.run.cloud.batch_config``, which needs the guard.
``gcp.py`` re-exports everything here, so ``execution.gcp`` remains the
reference point for callers.
"""

from epycloud.exceptions import ValidationError

# Families whose VMs can boot from ``hyperdisk-balanced``, which is the boot
# disk every Batch job in this pipeline requests. C4, C4D and N4/N4D are in
# fact Hyperdisk-*only*: they cannot boot on Persistent Disk at all.
HYPERDISK_MACHINE_FAMILIES = frozenset({"c3", "c3d", "c4", "c4d", "n4", "n4d"})

# Arm64 families. Hyperdisk-capable, but the pipeline image is amd64, so they
# fail for a different reason and get their own message.
ARM_MACHINE_FAMILIES = frozenset({"c4a", "n4a"})

# vCPU and memory (MiB) per candidate, read from the Compute API in
# us-central1-a, most recently on 2026-08-21. Kept here so resource safety can
# be asserted in tests without a network call. Re-read if a candidate is added.
MACHINE_SPECS: dict[str, tuple[int, int]] = {
    "c4d-standard-2": (2, 7168),
    "c4-standard-2": (2, 7168),
    "c3-highcpu-4": (4, 8192),
    "n4d-standard-2": (2, 8192),
    "n4-standard-2": (2, 8192),
    "c4d-standard-4": (4, 15360),
    "c4-standard-4": (4, 15360),
    "n4d-standard-4": (4, 16384),
    "n4-standard-4": (4, 16384),
    "c3-standard-4": (4, 16384),
    "c4d-standard-8": (8, 31744),
    "c4-standard-8": (8, 30720),
    "n4d-standard-8": (8, 32768),
    "n4-standard-8": (8, 32768),
    "c3-standard-8": (8, 32768),
    "c3d-standard-8": (8, 32768),
    "c3-highmem-4": (4, 32768),
    "c3d-highmem-4": (4, 32768),
    "n4d-highmem-4": (4, 32768),
    "n4-highmem-4": (4, 32768),
    "c4d-highmem-4": (4, 31744),
    "c4-highmem-4": (4, 31744),
}

# Ordered candidate pools, keyed by the largest workload requirement each pool
# can serve. Choosing by CPU and memory allows a memory-bound workload to move
# from standard-8 to highmem-4 without lowering either requirement.
MACHINE_CHAINS_BY_REQUIREMENT: dict[tuple[int, int], tuple[str, ...]] = {
    (2000, 8192): (
        "c4d-standard-2",
        "c3-highcpu-4",
        "n4d-standard-2",
        "n4-standard-2",
    ),
    (4000, 16384): (
        "c4d-standard-4",
        "c3-standard-4",
        "n4d-standard-4",
        "n4-standard-4",
    ),
    (4000, 32768): (
        "c3-highmem-4",
        "c3d-highmem-4",
        "n4d-highmem-4",
        "n4-highmem-4",
    ),
    (8000, 32768): (
        "c4d-standard-8",
        "c3-standard-8",
        "c3d-standard-8",
        "n4d-standard-8",
    ),
}

# Default chain per stage, matching the machine types in the shipped config
# template. Migration chooses a different pool when a profile raises a stage's
# CPU or memory requirement.
STAGE_MACHINE_CHAINS: dict[str, tuple[str, ...]] = {
    "a": MACHINE_CHAINS_BY_REQUIREMENT[(2000, 8192)],
    "b": MACHINE_CHAINS_BY_REQUIREMENT[(2000, 8192)],
    "c": MACHINE_CHAINS_BY_REQUIREMENT[(4000, 16384)],
}


def get_machine_family(machine_type: str) -> str:
    """
    Extract the family prefix from a machine type.

    Parameters
    ----------
    machine_type : str
        Machine type such as ``"c4d-standard-2"``.

    Returns
    -------
    str
        Family prefix (``"c4d"``), or an empty string if the value has no
        recognisable ``family-`` prefix.

    Examples
    --------
    >>> get_machine_family("c4d-standard-2")
    'c4d'
    >>> get_machine_family("")
    ''
    """
    return machine_type.strip().split("-", 1)[0].lower() if "-" in machine_type else ""


def get_candidate_chain(min_cpu_milli: int, min_memory_mib: int) -> tuple[str, ...]:
    """Return the smallest candidate pool that satisfies a workload.

    Parameters
    ----------
    min_cpu_milli : int
        Minimum CPU required by the stage.
    min_memory_mib : int
        Minimum memory required by the stage.

    Returns
    -------
    tuple of str
        Ordered candidates whose recorded resources meet both minima. Empty
        when no maintained pool can serve the workload.

    Examples
    --------
    >>> get_candidate_chain(2000, 7168)
    ('c4d-standard-2', 'c3-highcpu-4', 'n4d-standard-2', 'n4-standard-2')
    >>> get_candidate_chain(4000, 31744)
    ('c3-highmem-4', 'c3d-highmem-4', 'n4d-highmem-4', 'n4-highmem-4')
    """
    if min_cpu_milli <= 0 or min_memory_mib <= 0:
        return ()

    for (max_cpu_milli, max_memory_mib), pool in MACHINE_CHAINS_BY_REQUIREMENT.items():
        if min_cpu_milli > max_cpu_milli or min_memory_mib > max_memory_mib:
            continue
        candidates = tuple(
            machine_type
            for machine_type in pool
            if MACHINE_SPECS[machine_type][0] * 1000 >= min_cpu_milli
            and MACHINE_SPECS[machine_type][1] >= min_memory_mib
        )
        if candidates:
            return candidates

    return ()


def is_hyperdisk_family(machine_type: str) -> bool:
    """
    Report whether a machine type can boot from ``hyperdisk-balanced``.

    Parameters
    ----------
    machine_type : str
        Machine type to check. An empty string means "auto-select" and is not
        a Hyperdisk family.

    Returns
    -------
    bool
        True when the family is one of :data:`HYPERDISK_MACHINE_FAMILIES`.

    Examples
    --------
    >>> is_hyperdisk_family("c4-standard-2")
    True
    >>> is_hyperdisk_family("n2-standard-2")
    False
    >>> is_hyperdisk_family("")
    False
    """
    return get_machine_family(machine_type) in HYPERDISK_MACHINE_FAMILIES


def _get_stage_key(stage_name: str) -> str | None:
    """Derive a chain key ("a"/"b"/"c") from a display name like "Stage B"."""
    key = stage_name.strip()[-1:].lower()
    return key if key in STAGE_MACHINE_CHAINS else None


def validate_hyperdisk_family(machine_type: str, stage_name: str = "Stage") -> str:
    """
    Reject machine types that cannot boot the pipeline's Hyperdisk boot disk.

    An empty machine type means "let Google Cloud auto-select" and is returned
    unchanged, so this must be called before any check that rejects empties.

    Parameters
    ----------
    machine_type : str
        Resolved machine type (from a CLI override *or* from config).
    stage_name : str, optional
        Display name used in the error message, e.g. ``"Stage B"``. Its final
        letter also selects the suggested fallback chain.

    Returns
    -------
    str
        The machine type, unchanged.

    Raises
    ------
    ValidationError
        If the machine type's family cannot boot from ``hyperdisk-balanced``.

    Examples
    --------
    >>> validate_hyperdisk_family("c4-standard-2", "Stage B")
    'c4-standard-2'
    >>> validate_hyperdisk_family("", "Stage B")
    ''
    """
    if not machine_type or not machine_type.strip():
        return machine_type

    machine_type = machine_type.strip()
    if is_hyperdisk_family(machine_type):
        return machine_type

    family = get_machine_family(machine_type) or machine_type
    supported = ", ".join(sorted(HYPERDISK_MACHINE_FAMILIES))

    if family in ARM_MACHINE_FAMILIES:
        reason = (
            f"Family {family} is Arm64 (Axion). The pipeline image is built for amd64, "
            "so containers would fail to start on it."
        )
    else:
        reason = (
            f"This pipeline boots VMs with bootDisk type 'hyperdisk-balanced'. "
            f"Families {supported} support it; {family} does not. Cloud Batch would "
            "accept the job and then fail VM creation, giving up after ~1080s and "
            "blaming the disk type. 20 minutes lost for a typo."
        )

    stage_key = _get_stage_key(stage_name)
    suggestion = ""
    if stage_key:
        chain = STAGE_MACHINE_CHAINS[stage_key]
        vcpu = chain[0].rsplit("-", 1)[-1]
        suggestion = f"\nUse one of: {', '.join(chain)}  (all {vcpu} vCPU)."

    raise ValidationError(
        f"{stage_name} machine type '{machine_type}' cannot be used.\n{reason}{suggestion}"
    )
