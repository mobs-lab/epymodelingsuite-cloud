"""Shared GCS listing and filtering operations.

Provides reusable functions for listing experiments and runs in GCS,
filtering by pattern, and parsing run IDs. Used by both the download
and experiment commands.
"""

import re
from datetime import datetime
from fnmatch import fnmatch

from google.cloud import storage

_RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[a-f0-9]{8}$")


def list_experiments(
    client: storage.Client,
    bucket_name: str,
    prefix: str,
    scan_prefix: str = "",
    max_depth: int = 10,
) -> list[str]:
    """List experiment directories under a GCS prefix.

    Recursively scans directories under prefix. A directory is identified as
    an experiment when its children match the run_id pattern
    (YYYYMMDD-HHMMSS-xxxxxxxx).

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    prefix : str
        GCS prefix to list under (e.g. "pipeline/flu/")
    scan_prefix : str
        Narrowing prefix relative to ``prefix`` (e.g. "202605" or
        "test/myexp"). When set, scanning starts at
        ``prefix + scan_prefix + "/"`` instead of ``prefix``, reducing
        the number of GCS API calls for specific patterns.
    max_depth : int
        Maximum recursion depth (default: 10)

    Returns
    -------
    list[str]
        List of experiment paths relative to prefix
        (e.g. "202605/exp1", "test/myexperiments/exp1")
    """
    bucket = client.bucket(bucket_name)
    experiments: list[str] = []

    start_prefix = prefix
    if scan_prefix:
        start_prefix = prefix + scan_prefix
        if not start_prefix.endswith("/"):
            start_prefix += "/"

    def _scan(current_prefix: str, depth: int) -> None:
        if depth >= max_depth:
            return
        blobs = bucket.list_blobs(prefix=current_prefix, delimiter="/")
        for _ in blobs:
            pass
        child_prefixes = list(blobs.prefixes)
        if not child_prefixes:
            return

        child_names = [p[len(current_prefix) :].rstrip("/") for p in child_prefixes]

        if any(_RUN_ID_RE.match(name) for name in child_names):
            exp_rel = current_prefix[len(prefix) :].rstrip("/")
            if exp_rel:
                experiments.append(exp_rel)
            return

        for child in child_prefixes:
            _scan(child, depth + 1)

    _scan(start_prefix, 0)
    return sorted(experiments)


def list_run_ids(
    client: storage.Client,
    bucket_name: str,
    exp_path: str,
) -> list[str]:
    """List run_id directories under an experiment path.

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    exp_path : str
        Full experiment path (e.g. "pipeline/flu/202606/ed_smc_rmse_...")

    Returns
    -------
    list[str]
        List of run_id directory names, sorted lexicographically
    """
    bucket = client.bucket(bucket_name)
    prefix = exp_path if exp_path.endswith("/") else exp_path + "/"
    blobs = bucket.list_blobs(prefix=prefix, delimiter="/")

    for _ in blobs:
        pass

    run_ids = []
    for run_prefix in blobs.prefixes:
        run_id = run_prefix[len(prefix) :].rstrip("/")
        if run_id:
            run_ids.append(run_id)

    return sorted(run_ids)


def filter_experiments(experiments: list[str], patterns: str | list[str]) -> list[str]:
    """Filter experiment names using fnmatch pattern(s).

    Parameters
    ----------
    experiments : list[str]
        List of experiment names
    patterns : str or list[str]
        Glob pattern or list of patterns (fnmatch-compatible)

    Returns
    -------
    list[str]
        Filtered list of experiment names matching any of the patterns
    """
    if isinstance(patterns, str):
        patterns = [patterns]
    return [exp for exp in experiments if any(fnmatch(exp, p) for p in patterns)]


def extract_scan_prefix(patterns: list[str]) -> str:
    """Extract the common literal directory prefix from patterns.

    For each pattern, finds the longest path component that contains no
    wildcard characters. Returns the shortest such prefix across all
    patterns so the scan covers all of them.

    Examples
    --------
    >>> extract_scan_prefix(["202605/*"])
    '202605'
    >>> extract_scan_prefix(["test/reff_resimm_beta"])
    'test/reff_resimm_beta'
    >>> extract_scan_prefix(["test/myexp/*", "test/myexp"])
    'test/myexp'
    >>> extract_scan_prefix(["*"])
    ''
    """
    if not patterns:
        return ""

    prefixes: list[str] = []
    for p in patterns:
        # Find position of first wildcard character
        wildcard_pos = len(p)
        for i, ch in enumerate(p):
            if ch in ("*", "?", "["):
                wildcard_pos = i
                break

        literal = p[:wildcard_pos]

        if wildcard_pos < len(p):
            # Has wildcards: truncate to last / to get a directory boundary
            slash_pos = literal.rfind("/")
            prefixes.append(literal[:slash_pos] if slash_pos >= 0 else "")
        else:
            # No wildcards: entire string is the prefix
            prefixes.append(literal)

    # Return shortest prefix (covers all patterns)
    return min(prefixes, key=len)


def normalize_filter_patterns(raw_pattern: str) -> list[str]:
    """Normalize a user-provided filter pattern into fnmatch pattern(s).

    Handles trailing slashes and bare strings by expanding them into
    patterns that match both exact and child experiments.

    - Trailing slash: "foo/" -> ["foo/*", "foo"]
    - No wildcards:   "foo"  -> ["foo", "foo/*"]
    - Has wildcards:  "foo*" -> ["foo*"]

    Parameters
    ----------
    raw_pattern : str
        User-provided filter string

    Returns
    -------
    list[str]
        List of fnmatch-compatible patterns
    """
    if raw_pattern.endswith("/"):
        return [raw_pattern + "*", raw_pattern.rstrip("/")]
    elif any(ch in raw_pattern for ch in ("*", "?", "[")):
        return [raw_pattern]
    else:
        return [raw_pattern, raw_pattern + "/*"]


def list_experiment_runs(
    client: storage.Client,
    bucket_name: str,
    prefix: str,
    scan_prefix: str = "",
) -> list[tuple[str, str]]:
    """List (experiment, run_id) pairs using flat blob listing.

    Much faster than calling list_experiments() + list_run_ids() for each,
    as it uses a single paginated API call instead of O(directories) calls.
    Blob paths are parsed to extract experiment paths and run IDs.

    Parameters
    ----------
    client : storage.Client
        GCS client
    bucket_name : str
        GCS bucket name
    prefix : str
        GCS prefix (e.g. "pipeline/flu/")
    scan_prefix : str
        Narrowing prefix relative to ``prefix`` (e.g. "202605")

    Returns
    -------
    list[tuple[str, str]]
        Sorted list of (experiment_path, run_id) pairs, where
        experiment_path is relative to prefix
    """
    bucket = client.bucket(bucket_name)

    start_prefix = prefix
    if scan_prefix:
        start_prefix = prefix + scan_prefix
        if not start_prefix.endswith("/"):
            start_prefix += "/"

    # Flat listing: single paginated API stream, no delimiter
    blobs = bucket.list_blobs(prefix=start_prefix)

    seen: set[tuple[str, str]] = set()
    for blob in blobs:
        rel_path = blob.name[len(prefix):]
        parts = rel_path.split("/")

        # Find the first path component matching run_id pattern
        for i, part in enumerate(parts):
            if i > 0 and _RUN_ID_RE.match(part):
                exp_path = "/".join(parts[:i])
                seen.add((exp_path, part))
                break

    return sorted(seen)


def parse_run_id_datetime(run_id: str) -> datetime | None:
    """Parse a run ID into a datetime.

    Run IDs have the format YYYYMMDD-HHMMSS-xxxxxxxx.

    Parameters
    ----------
    run_id : str
        Run ID string (e.g. "20260218-143052-a1b2c3d4")

    Returns
    -------
    datetime or None
        Parsed datetime, or None if the format doesn't match
    """
    if not _RUN_ID_RE.match(run_id):
        return None
    try:
        return datetime.strptime(run_id[:15], "%Y%m%d-%H%M%S")
    except ValueError:
        return None
