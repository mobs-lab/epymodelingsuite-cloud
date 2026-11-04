"""Check server-side publication without contacting a registry."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "regions,fail", [("", False), ("us-east4 us-east5", False), ("us-east4 us-east5", True)]
)
def test_publish_same_image(tmp_path, regions, fail):
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\n'
        'if [ "$FAIL" = true ] && [ "$1" = push ] && [ "$2" != source ]; then exit 1; fi\n'
    )
    docker.chmod(0o755)
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(ROOT / "docker/replicate-built-image.sh")],
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "CALLS": str(calls),
            "FAIL": str(fail).lower(),
            "SOURCE_IMAGE": "source",
            "IMAGE_PATH": "project/repo/image:dev",
            "REPLICA_REGIONS": regions,
        },
    )
    expected = ["push source"]
    for region in regions.split():
        destination = f"{region}-docker.pkg.dev/project/repo/image:dev"
        expected += [f"tag source {destination}", f"push {destination}"]
        if fail:
            break
    assert calls.read_text().splitlines() == expected
    assert result.returncode == (1 if fail else 0)
