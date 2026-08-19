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
# us-central1-a on 2026-08-19. Kept here so the memory-non-decreasing rule can
# be asserted in tests without a network call. Re-read if a candidate is added.
MACHINE_SPECS: dict[str, tuple[int, int]] = {
    "c4d-standard-2": (2, 7168),
    "c4-standard-2": (2, 7168),
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
}

# Ordered in-region fallback candidates, keyed by machine size.
#
# Chains are per size, not per stage, because a stage's size is a config choice.
# The flu profile runs Stage C on c4d-standard-8 for memory headroom, so pinning
# Stage C to a standard-4 chain would make every fallback a silent downgrade.
#
# Position 2 at standard-2 and standard-4 is C4, not N4D. A capacity probe on
# 2026-08-18 that created VMs directly (bypassing Batch) found us-central1
# unable to supply a *single* c4d-standard-2, n4d-standard-2 or n4-standard-2,
# while c4-standard-2 returned 10 of 10 instantly. At those two sizes C4 is a
# spec-identical drop-in for C4D (2 / 7168 and 4 / 15360 respectively), so it
# costs nothing in requested resources.
#
# C4 is deliberately absent from the standard-8 chain: c4-standard-8 is 30720
# MiB against c4d-standard-8's 31744, so it would *lower* available memory.
# Memory must be non-decreasing along a chain or fallback turns a capacity
# failure into an OOM. C3 takes position 2 there instead, being the only other
# family the probe found available in us-central1.
#
# Sizes below standard-4 cannot serve Stage C: 2 vCPU cannot satisfy its 4000
# mCPU request. c3-standard-2 does not exist, which is why C3 appears only in
# the larger chains.
#
# CAPACITY CAVEAT: only the standard-2 and standard-4 candidates were probed.
# Capacity thins with machine size, so the standard-8 chain is ordered on specs
# and family availability, not on a measurement. Re-probe whenever a chain is
# edited or a region is added. A chain whose members are all starved is worse
# than no chain, since it consumes the full stall budget per candidate and
# still fails.
MACHINE_CHAINS_BY_SIZE: dict[str, tuple[str, ...]] = {
    "standard-2": ("c4d-standard-2", "c4-standard-2", "n4d-standard-2", "n4-standard-2"),
    "standard-4": ("c4d-standard-4", "c4-standard-4", "n4d-standard-4", "c3-standard-4"),
    "standard-8": ("c4d-standard-8", "c3-standard-8", "c3d-standard-8", "n4d-standard-8"),
}

# Default chain per stage, matching the machine types in the shipped config
# template. A profile that configures a different size gets its chain from
# chain_for() instead, which is what the fallback loop must use.
STAGE_MACHINE_CHAINS: dict[str, tuple[str, ...]] = {
    "a": MACHINE_CHAINS_BY_SIZE["standard-2"],
    "b": MACHINE_CHAINS_BY_SIZE["standard-2"],
    "c": MACHINE_CHAINS_BY_SIZE["standard-4"],
}


def machine_family(machine_type: str) -> str:
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
    >>> machine_family("c4d-standard-2")
    'c4d'
    >>> machine_family("")
    ''
    """
    return machine_type.strip().split("-", 1)[0].lower() if "-" in machine_type else ""


def machine_size(machine_type: str) -> str:
    """
    Extract the size suffix from a machine type.

    Parameters
    ----------
    machine_type : str
        Machine type such as ``"c4d-standard-8"``.

    Returns
    -------
    str
        Size suffix (``"standard-8"``), or an empty string when the value has
        no ``family-size`` shape.

    Examples
    --------
    >>> machine_size("c4d-standard-8")
    'standard-8'
    >>> machine_size("bogus")
    ''
    """
    parts = machine_type.strip().lower().split("-", 1)
    return parts[1] if len(parts) == 2 and parts[1] else ""


def chain_for(machine_type: str) -> tuple[str, ...]:
    """
    Return the fallback candidates for a configured machine type.

    Candidates keep the size and vary only the family, so memory and vCPU never
    drop mid-fallback. A machine type with no known chain falls back to itself,
    which is the same behaviour as pinning it.

    Parameters
    ----------
    machine_type : str
        Configured machine type. An empty string means auto-select, which has
        no chain.

    Returns
    -------
    tuple of str
        Ordered candidates, starting with ``machine_type`` when it is a member
        of its size's chain. Empty when ``machine_type`` is empty.

    Examples
    --------
    >>> chain_for("c4d-standard-8")
    ('c4d-standard-8', 'c3-standard-8', 'c3d-standard-8', 'n4d-standard-8')
    >>> chain_for("c4-standard-2")
    ('c4-standard-2', 'c4d-standard-2', 'n4d-standard-2', 'n4-standard-2')
    >>> chain_for("")
    ()
    """
    machine_type = machine_type.strip().lower()
    if not machine_type:
        return ()

    chain = MACHINE_CHAINS_BY_SIZE.get(machine_size(machine_type))
    if not chain:
        return (machine_type,)
    if machine_type not in chain:
        return (machine_type,)

    # Start from the configured type, then the rest in their probed order.
    return (machine_type,) + tuple(c for c in chain if c != machine_type)


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
    return machine_family(machine_type) in HYPERDISK_MACHINE_FAMILIES


def _stage_key(stage_name: str) -> str | None:
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

    family = machine_family(machine_type) or machine_type
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

    stage_key = _stage_key(stage_name)
    suggestion = ""
    if stage_key:
        chain = STAGE_MACHINE_CHAINS[stage_key]
        vcpu = chain[0].rsplit("-", 1)[-1]
        suggestion = f"\nUse one of: {', '.join(chain)}  (all {vcpu} vCPU)."

    raise ValidationError(
        f"{stage_name} machine type '{machine_type}' cannot be used.\n{reason}{suggestion}"
    )
