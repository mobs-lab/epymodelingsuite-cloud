"""Cloud Build execution for build command."""

import subprocess
import sys
from pathlib import Path

from epycloud.lib.output import Colors, ask_confirmation, colorize, error, info, success, warning


def build_cloud(
    project_id: str,
    region: str,
    repo_name: str,
    image_name: str,
    image_tag: str,
    image_path: str,
    modeling_suite_repo: str,
    modeling_suite_ref: str,
    no_cache: bool,
    wait: bool,
    verbose: bool,
    dry_run: bool,
    dockerfile_path: Path,
    context_path: Path,
) -> int:
    """Build with Cloud Build (async by default).

    Parameters
    ----------
    project_id : str
        GCP project ID
    region : str
        GCP region
    repo_name : str
        Artifact Registry repo name
    image_name : str
        Image name
    image_tag : str
        Image tag
    image_path : str
        Full image path
    modeling_suite_repo : str
        GitHub modeling suite repo
    modeling_suite_ref : str
        Modeling suite ref
    no_cache : bool
        Disable cache
    wait : bool
        Wait for completion
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
    cloudbuild_yaml = context_path / "cloudbuild.yaml"
    missing_files = []

    if not cloudbuild_yaml.exists():
        missing_files.append(f"cloudbuild.yaml (expected at: {cloudbuild_yaml})")

    if not dockerfile_path.exists():
        missing_files.append(f"Dockerfile (expected at: {dockerfile_path})")

    if missing_files:
        for file in missing_files:
            error(f"Required file not found: {file}")
        error("You must run this command from the epymodelingsuite-cloud repository")
        info(f"Current directory: {Path.cwd()}")
        return 1

    # Display build information
    print("Build with Cloud Build")
    print()
    print(colorize("[Configuration]", Colors.CYAN))
    info(f"Image: {image_path}")
    info(f"Dockerfile: {dockerfile_path}")
    info(f"Context: {context_path}")

    if modeling_suite_repo:
        info(f"Repository: {modeling_suite_repo} @ {modeling_suite_ref}")
    else:
        info("Repository: not configured")

    if no_cache:
        info("Cache: disabled (default)")
    else:
        info("Cache: enabled (--cache)")

    async_mode = "async" if not wait else "sync (--wait)"
    info(f"Mode: {async_mode}")
    print()

    # Ask for confirmation before proceeding
    if not dry_run:
        if not ask_confirmation("Continue?", default=True):
            info("Build cancelled")
            return 0
        print()

    # Build substitutions string
    no_cache_str = "true" if no_cache else "false"
    substitutions = (
        f"_REGION={region},"
        f"_REPO_NAME={repo_name},"
        f"_IMAGE_NAME={image_name},"
        f"_IMAGE_TAG={image_tag},"
        f"_GITHUB_MODELING_SUITE_REPO={modeling_suite_repo},"
        f"_GITHUB_MODELING_SUITE_REF={modeling_suite_ref},"
        f"_NO_CACHE={no_cache_str}"
    )

    # Build gcloud command with absolute context path
    cmd = [
        "gcloud",
        "builds",
        "submit",
        f"--project={project_id}",
        f"--region={region}",
        f"--config={context_path / 'cloudbuild.yaml'}",
        f"--substitutions={substitutions}",
        str(context_path),
    ]

    if not wait:
        cmd.append("--async")
        cmd.append("--format=value(id)")

    if dry_run:
        info(f"Would execute: {' '.join(cmd)}")
        return 0

    # Execute command (no directory change needed)
    result = subprocess.run(
        cmd,
        capture_output=not wait,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error("Cloud Build submission failed")
        if verbose and result.stderr:
            print(result.stderr, file=sys.stderr)
        return 1

    if wait:
        success("Build completed successfully!")
    else:
        # Parse build ID from output
        build_id = result.stdout.strip() if result.stdout else None

        if build_id:
            success("Build submitted successfully!")
            info(f"Build ID: {build_id}")
            print()
            info("Monitor with:")
            info(f"  gcloud builds describe {build_id} --region={region}")
            info(f"  gcloud builds log {build_id} --region={region} --stream")
            info(f"  gcloud builds list --region={region} --ongoing")
        else:
            warning("Build submitted but could not parse build ID")

    return 0
