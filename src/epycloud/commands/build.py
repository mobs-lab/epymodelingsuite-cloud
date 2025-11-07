"""Build command for Docker image management."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_project_root,
    require_config,
)
from epycloud.lib.output import error, info, success, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the build command parser.

    Args:
        subparsers: Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "build",
        help="Build and push Docker images",
        description=(
            "Build Docker images for the pipeline with three modes: "
            "cloud (Cloud Build), local (build + push), dev (local only)"
        ),
    )

    parser.add_argument(
        "mode",
        nargs="?",
        choices=["cloud", "local", "dev"],
        default="cloud",
        help="Build mode: cloud (default, async), local (build + push), dev (local only)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable build cache",
    )

    parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )

    parser.add_argument(
        "--push",
        action="store_true",
        help="Push to registry (for dev builds)",
    )

    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Don't push to registry (for local builds)",
    )

    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for build to complete (cloud builds)",
    )


def handle(ctx: dict[str, Any]) -> int:
    """Handle the build command.

    Args:
        ctx: Command context with config and args

    Returns:
        Exit code (0 for success)
    """
    args = ctx["args"]
    verbose = ctx["verbose"]
    dry_run = ctx["dry_run"]

    try:
        config = require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    # Get mode (default: cloud)
    mode = args.mode

    # Get Docker config
    docker_config = config.get("docker", {})
    google_cloud_config = config.get("google_cloud", {})
    github_config = config.get("github", {})

    # Build image information
    registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")
    repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
    image_name = docker_config.get("image_name", "epymodelingsuite")
    image_tag = args.tag or docker_config.get("image_tag", "latest")

    # GitHub modeling suite repo (optional)
    modeling_suite_repo = github_config.get("modeling_suite_repo", "")
    modeling_suite_ref = github_config.get("modeling_suite_ref", "main")

    # Validate required config
    if not project_id:
        error("google_cloud.project_id not configured")
        info("Set it with: epycloud config set google_cloud.project_id YOUR_PROJECT_ID")
        return 2

    # Construct image path
    if mode in ["cloud", "local"]:
        image_path = f"{registry}/{project_id}/{repo_name}/{image_name}:{image_tag}"
    else:  # dev mode
        image_path = f"{image_name}:local"

    # Get project root (where Makefile and docker/ dir are)
    project_root = get_project_root()

    # Get GitHub PAT from environment or secrets
    github_pat = os.environ.get("GITHUB_PAT") or os.environ.get("EPYCLOUD_GITHUB_PAT")
    if not github_pat and modeling_suite_repo:
        # Check secrets config
        secrets = config.get("_secrets", {})
        github_pat = secrets.get("github", {}).get("personal_access_token")

    # Validate GitHub PAT if modeling suite is configured
    if modeling_suite_repo and not github_pat:
        error("GitHub PAT required when modeling_suite_repo is configured")
        info("Set GITHUB_PAT environment variable or add to secrets.yaml")
        return 2

    # Execute build based on mode
    if mode == "cloud":
        return _build_cloud(
            project_id=project_id,
            region=region,
            repo_name=repo_name,
            image_name=image_name,
            image_tag=image_tag,
            image_path=image_path,
            modeling_suite_repo=modeling_suite_repo,
            modeling_suite_ref=modeling_suite_ref,
            no_cache=args.no_cache,
            wait=args.wait,
            verbose=verbose,
            dry_run=dry_run,
            project_root=project_root,
        )
    elif mode == "local":
        return _build_local(
            image_path=image_path,
            modeling_suite_repo=modeling_suite_repo,
            modeling_suite_ref=modeling_suite_ref,
            github_pat=github_pat,
            no_cache=args.no_cache,
            push=not args.no_push,
            verbose=verbose,
            dry_run=dry_run,
            project_root=project_root,
        )
    else:  # dev
        return _build_dev(
            image_name=image_name,
            image_path=image_path,
            modeling_suite_repo=modeling_suite_repo,
            modeling_suite_ref=modeling_suite_ref,
            github_pat=github_pat,
            no_cache=args.no_cache,
            push=args.push,
            verbose=verbose,
            dry_run=dry_run,
            project_root=project_root,
        )


def _build_cloud(
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
    project_root: Path,
) -> int:
    """Build with Cloud Build (async by default).

    Args:
        project_id: GCP project ID
        region: GCP region
        repo_name: Artifact Registry repo name
        image_name: Image name
        image_tag: Image tag
        image_path: Full image path
        modeling_suite_repo: GitHub modeling suite repo
        modeling_suite_ref: Modeling suite ref
        no_cache: Disable cache
        wait: Wait for completion
        verbose: Verbose output
        dry_run: Dry run mode
        project_root: Project root directory

    Returns:
        Exit code
    """
    info(f"Building with Cloud Build (async: {not wait})...")
    info(f"Image: {image_path}")

    if modeling_suite_repo:
        info(f"Repository: {modeling_suite_repo} @ {modeling_suite_ref}")
    else:
        info("Repository: not configured")

    if no_cache:
        warning("Cache disabled (--no-cache)")

    # Build gcloud command
    cmd = [
        "gcloud",
        "builds",
        "submit",
        f"--project={project_id}",
        f"--region={region}",
        "--config=cloudbuild.yaml",
        f"--substitutions=_REGION={region},_REPO_NAME={repo_name},_IMAGE_NAME={image_name},_IMAGE_TAG={image_tag},_GITHUB_MODELING_SUITE_REPO={modeling_suite_repo},_GITHUB_MODELING_SUITE_REF={modeling_suite_ref}",
    ]

    if not wait:
        cmd.append("--async")
        cmd.append("--format=value(id)")

    if dry_run:
        info(f"Would execute: {' '.join(cmd)}")
        return 0

    # Change to project root
    original_dir = Path.cwd()
    try:
        os.chdir(project_root)

        # Execute command
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

    finally:
        os.chdir(original_dir)


def _build_local(
    image_path: str,
    modeling_suite_repo: str,
    modeling_suite_ref: str,
    github_pat: str,
    no_cache: bool,
    push: bool,
    verbose: bool,
    dry_run: bool,
    project_root: Path,
) -> int:
    """Build locally and push to Artifact Registry.

    Args:
        image_path: Full image path
        modeling_suite_repo: GitHub modeling suite repo
        modeling_suite_ref: Modeling suite ref
        github_pat: GitHub personal access token
        no_cache: Disable cache
        push: Push to registry
        verbose: Verbose output
        dry_run: Dry run mode
        project_root: Project root directory

    Returns:
        Exit code
    """
    info("Building cloud image locally...")
    info(f"Image: {image_path}")

    if modeling_suite_repo:
        info(f"Repository: {modeling_suite_repo} @ {modeling_suite_ref}")
    else:
        info("Repository: not configured")

    if no_cache:
        warning("Cache disabled (--no-cache)")

    if not push:
        warning("Will not push to registry (--no-push)")

    # Build docker command
    cmd = [
        "docker",
        "buildx",
        "build",
        "--platform=linux/amd64",
        f"-t={image_path}",
        "--target=cloud",
        "-f=docker/Dockerfile",
    ]

    if no_cache:
        cmd.append("--no-cache")

    if modeling_suite_repo:
        cmd.append(f"--build-arg=GITHUB_MODELING_SUITE_REPO={modeling_suite_repo}")
        cmd.append(f"--build-arg=GITHUB_MODELING_SUITE_REF={modeling_suite_ref}")
        cmd.append(f"--build-arg=GITHUB_PAT={github_pat}")

    if push:
        cmd.append("--push")

    cmd.append(".")

    if dry_run:
        # Mask GitHub PAT in output
        cmd_display = [
            arg.replace(github_pat, "***") if github_pat and github_pat in arg else arg
            for arg in cmd
        ]
        info(f"Would execute: {' '.join(cmd_display)}")
        return 0

    # Change to project root
    original_dir = Path.cwd()
    try:
        os.chdir(project_root)

        # Execute command
        result = subprocess.run(cmd, check=False)

        if result.returncode != 0:
            error("Docker build failed")
            return 1

        if push:
            success(f"Image built and pushed: {image_path}")
        else:
            success(f"Image built: {image_path}")
            info("Use --push to push to registry")

        return 0

    finally:
        os.chdir(original_dir)


def _build_dev(
    image_name: str,
    image_path: str,
    modeling_suite_repo: str,
    modeling_suite_ref: str,
    github_pat: str,
    no_cache: bool,
    push: bool,
    verbose: bool,
    dry_run: bool,
    project_root: Path,
) -> int:
    """Build dev image locally (no push by default).

    Args:
        image_name: Image name
        image_path: Full image path
        modeling_suite_repo: GitHub modeling suite repo
        modeling_suite_ref: Modeling suite ref
        github_pat: GitHub personal access token
        no_cache: Disable cache
        push: Push to registry
        verbose: Verbose output
        dry_run: Dry run mode
        project_root: Project root directory

    Returns:
        Exit code
    """
    info("Building local development image...")
    info(f"Image: {image_path}")
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

    # Build docker command
    cmd = [
        "docker",
        "build",
        f"-t={image_path}",
        "--target=local",
        "-f=docker/Dockerfile",
    ]

    if no_cache:
        cmd.append("--no-cache")

    if modeling_suite_repo:
        cmd.append(f"--build-arg=GITHUB_MODELING_SUITE_REPO={modeling_suite_repo}")
        cmd.append(f"--build-arg=GITHUB_MODELING_SUITE_REF={modeling_suite_ref}")
        cmd.append(f"--build-arg=GITHUB_PAT={github_pat}")

    cmd.append(".")

    if dry_run:
        # Mask GitHub PAT in output
        cmd_display = [
            arg.replace(github_pat, "***") if github_pat and github_pat in arg else arg
            for arg in cmd
        ]
        info(f"Would execute: {' '.join(cmd_display)}")
        return 0

    # Change to project root
    original_dir = Path.cwd()
    try:
        os.chdir(project_root)

        # Execute command
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

    finally:
        os.chdir(original_dir)
