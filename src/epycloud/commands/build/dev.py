"""Development build execution for build command."""

import subprocess
from pathlib import Path

from epycloud.lib.command_helpers import check_docker_available
from epycloud.lib.output import error, info, success, warning


def build_dev(
    image_name: str,
    image_path: str,
    modeling_suite_repo: str,
    modeling_suite_ref: str,
    github_pat: str,
    no_cache: bool,
    push: bool,
    verbose: bool,
    dry_run: bool,
    dockerfile_path: Path,
    context_path: Path,
) -> int:
    """Build dev image locally (no push by default).

    Parameters
    ----------
    image_name : str
        Image name
    image_path : str
        Full image path
    modeling_suite_repo : str
        GitHub modeling suite repo
    modeling_suite_ref : str
        Modeling suite ref
    github_pat : str
        GitHub personal access token
    no_cache : bool
        Disable cache
    push : bool
        Push to registry
    verbose : bool
        Verbose output
    dry_run : bool
        Dry run mode
    dockerfile_path : Path
        Absolute path to Dockerfile
    context_path : Path
        Absolute path to build context directory

    Returns
    -------
    int
        Exit code
    """
    # Validate required files exist before attempting build
    if not dockerfile_path.exists():
        error(f"Required file not found: Dockerfile (expected at: {dockerfile_path})")
        error("You must run this command from the epymodelingsuite-cloud repository")
        info(f"Current directory: {Path.cwd()}")
        return 1

    # Check Docker availability
    if not dry_run and not check_docker_available():
        error("Docker is not installed or not in PATH")
        info("Install Docker Engine or OrbStack (macOS)")
        return 1

    info("Building local development image...")
    info(f"Image: {image_path}")
    info(f"Dockerfile: {dockerfile_path}")
    info(f"Context: {context_path}")
    info("Target: local (no gcloud)")

    if modeling_suite_repo:
        info(f"Repository: {modeling_suite_repo} @ {modeling_suite_ref}")
    else:
        info("Repository: not configured")

    if no_cache:
        warning("Cache disabled (--no-cache)")
    else:
        info("Cache: enabled")

    if push:
        warning("Will push to registry (--push)")

    # Build docker command with absolute paths
    cmd = [
        "docker",
        "build",
        f"-t={image_path}",
        "--target=local",
        f"-f={dockerfile_path}",
    ]

    if no_cache:
        cmd.append("--no-cache")

    if modeling_suite_repo:
        cmd.append(f"--build-arg=GITHUB_MODELING_SUITE_REPO={modeling_suite_repo}")
        cmd.append(f"--build-arg=GITHUB_MODELING_SUITE_REF={modeling_suite_ref}")
        cmd.append(f"--build-arg=GITHUB_PAT={github_pat}")

    cmd.append(str(context_path))

    if dry_run:
        # Mask GitHub PAT in output
        cmd_display = [
            arg.replace(github_pat, "***") if github_pat and github_pat in arg else arg
            for arg in cmd
        ]
        info(f"Would execute: {' '.join(cmd_display)}")
        return 0

    # Execute command (no directory change needed)
    result = subprocess.run(cmd, check=False)

    if result.returncode != 0:
        error("Docker build failed")
        return 1

    success(f"Local image built: {image_path}")
    info("Use with: docker compose or epycloud run --local")

    if push:
        # Push the image
        info(f"Pushing {image_path}...")
        push_result = subprocess.run(["docker", "push", image_path], check=False)

        if push_result.returncode != 0:
            error("Docker push failed")
            return 1

        success(f"Image pushed: {image_path}")

    return 0
