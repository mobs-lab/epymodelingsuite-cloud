"""Build command for Docker image management.

Available commands:
    epycloud build cloud     Submit to Cloud Build (async, default)
    epycloud build local     Build locally and push to registry
    epycloud build dev       Build locally only (no push)
    epycloud build status    Display recent/ongoing Cloud Build jobs
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from epycloud.exceptions import ConfigError
from epycloud.lib.command_helpers import (
    get_docker_config,
    get_github_config,
    get_github_pat,
    get_image_uri,
    get_project_root,
    require_config,
)
from epycloud.lib.formatters import (
    create_subparsers,
    format_duration,
    format_status,
    format_timestamp_full,
)
from epycloud.lib.output import error, info, success, warning


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the build command parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        Subparser action from main parser
    """
    parser = subparsers.add_parser(
        "build",
        help="Build and manage Docker images",
        description="Build Docker images and manage Cloud Build jobs",
    )

    # Store parser for help printing
    parser.set_defaults(_build_parser=parser)

    # Create subcommands with consistent formatting
    build_subparsers = create_subparsers(parser, "build_subcommand")

    # epycloud build cloud
    cloud_parser = build_subparsers.add_parser(
        "cloud",
        help="Submit to Cloud Build (async)",
        description="Build with Cloud Build (async by default)",
    )
    cloud_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable build cache",
    )
    cloud_parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )
    cloud_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for build to complete",
    )

    # epycloud build local
    local_parser = build_subparsers.add_parser(
        "local",
        help="Build locally and push to registry",
        description="Build locally and push to Artifact Registry",
    )
    local_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable build cache",
    )
    local_parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )
    local_parser.add_argument(
        "--no-push",
        action="store_true",
        help="Don't push to registry",
    )

    # epycloud build dev
    dev_parser = build_subparsers.add_parser(
        "dev",
        help="Build locally only (no push)",
        description="Build local development image (no push by default)",
    )
    dev_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable build cache",
    )
    dev_parser.add_argument(
        "--tag",
        help="Image tag (default: from config)",
    )
    dev_parser.add_argument(
        "--push",
        action="store_true",
        help="Push to registry",
    )

    # epycloud build status
    status_parser = build_subparsers.add_parser(
        "status",
        help="Display recent/ongoing Cloud Build jobs",
        description="Display recent/ongoing Cloud Build jobs",
    )
    status_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of builds to display (default: 10)",
    )
    status_parser.add_argument(
        "--ongoing",
        action="store_true",
        help="Show only active builds (QUEUED, WORKING)",
    )


def handle(ctx: dict[str, Any]) -> int:
    """Handle the build command and route to appropriate subcommand.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context with config and args

    Returns
    -------
    int
        Exit code (0 for success)
    """
    args = ctx["args"]

    # Check if subcommand is provided
    if not hasattr(args, "build_subcommand") or args.build_subcommand is None:
        # Print help if no subcommand
        if hasattr(args, "_build_parser"):
            args._build_parser.print_help()
        return 1

    # Route to subcommand handlers
    if args.build_subcommand == "cloud":
        return _handle_cloud(ctx)
    elif args.build_subcommand == "local":
        return _handle_local(ctx)
    elif args.build_subcommand == "dev":
        return _handle_dev(ctx)
    elif args.build_subcommand == "status":
        return _handle_status(ctx)

    # Should never reach here
    error(f"Unknown build subcommand: {args.build_subcommand}")
    return 1


def _handle_cloud(ctx: dict[str, Any]) -> int:
    """Handle the cloud build subcommand.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context with config and args

    Returns
    -------
    int
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

    # Get config
    google_cloud = config.get("google_cloud", {})
    project_id = google_cloud.get("project_id")
    region = google_cloud.get("region", "us-central1")
    docker = get_docker_config(config)
    image_tag = args.tag or docker["image_tag"]
    github = get_github_config(config)
    modeling_suite_repo = github["modeling_suite_repo"]
    modeling_suite_ref = github["modeling_suite_ref"]

    # Validate required config
    if not project_id:
        error("google_cloud.project_id not configured")
        info("Set it with: epycloud config set google_cloud.project_id YOUR_PROJECT_ID")
        return 2

    # Construct image path
    image_path = get_image_uri(config, tag=image_tag)

    # Get project root (where Makefile and docker/ dir are)
    project_root = get_project_root()

    return _build_cloud(
        project_id=project_id,
        region=region,
        repo_name=docker["repo_name"],
        image_name=docker["image_name"],
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


def _handle_local(ctx: dict[str, Any]) -> int:
    """Handle the local build subcommand.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context with config and args

    Returns
    -------
    int
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

    # Get config
    google_cloud = config.get("google_cloud", {})
    project_id = google_cloud.get("project_id")
    docker = get_docker_config(config)
    image_tag = args.tag or docker["image_tag"]
    github = get_github_config(config)
    modeling_suite_repo = github["modeling_suite_repo"]
    modeling_suite_ref = github["modeling_suite_ref"]

    # Validate required config
    if not project_id:
        error("google_cloud.project_id not configured")
        info("Set it with: epycloud config set google_cloud.project_id YOUR_PROJECT_ID")
        return 2

    # Construct image path
    image_path = get_image_uri(config, tag=image_tag)

    # Get GitHub PAT
    github_pat = get_github_pat(config, required=bool(modeling_suite_repo))
    if modeling_suite_repo and not github_pat:
        return 2

    # Get project root (where Makefile and docker/ dir are)
    project_root = get_project_root()

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


def _handle_dev(ctx: dict[str, Any]) -> int:
    """Handle the dev build subcommand.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context with config and args

    Returns
    -------
    int
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

    # Get config
    docker = get_docker_config(config)
    image_name = docker["image_name"]
    image_tag = args.tag or "local"
    image_path = f"{image_name}:{image_tag}"
    github = get_github_config(config)
    modeling_suite_repo = github["modeling_suite_repo"]
    modeling_suite_ref = github["modeling_suite_ref"]

    # Get GitHub PAT
    github_pat = get_github_pat(config, required=bool(modeling_suite_repo))
    if modeling_suite_repo and not github_pat:
        return 2

    # Get project root (where Makefile and docker/ dir are)
    project_root = get_project_root()

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


def _handle_status(ctx: dict[str, Any]) -> int:
    """Handle the status subcommand.

    Parameters
    ----------
    ctx : dict[str, Any]
        Command context with config and args

    Returns
    -------
    int
        Exit code (0 for success)
    """
    args = ctx["args"]
    verbose = ctx["verbose"]

    try:
        config = require_config(ctx)
    except ConfigError as e:
        error(str(e))
        return 2

    google_cloud_config = config.get("google_cloud", {})
    project_id = google_cloud_config.get("project_id")
    region = google_cloud_config.get("region", "us-central1")

    # Validate required config
    if not project_id:
        error("google_cloud.project_id not configured")
        info("Set it with: epycloud config set google_cloud.project_id YOUR_PROJECT_ID")
        return 2

    # Build gcloud command
    cmd = [
        "gcloud",
        "builds",
        "list",
        f"--project={project_id}",
        f"--region={region}",
        f"--limit={args.limit}",
        "--format=json",
    ]

    if args.ongoing:
        cmd.append("--ongoing")

    if verbose:
        info(f"Executing: {' '.join(cmd)}")

    # Execute command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error("Failed to fetch build status")
            if verbose and result.stderr:
                print(result.stderr, file=sys.stderr)
            return 1

        # Parse JSON output
        builds = json.loads(result.stdout) if result.stdout else []

        # Display results
        _display_build_status(builds, args.limit)

        return 0

    except json.JSONDecodeError as e:
        error(f"Failed to parse gcloud output: {e}")
        if verbose:
            print(result.stdout, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Unexpected error: {e}")
        return 1


def _display_build_status(builds: list[dict], limit: int) -> None:
    """Format and display build status in table format.

    Parameters
    ----------
    builds : list[dict]
        List of build dictionaries from gcloud
    limit : int
        Limit used for query (for display message)
    """
    if not builds:
        info("No builds found")
        return

    print()
    info("Recent Cloud Builds")
    print("=" * 100)
    print()

    # Header
    print(f"{'BUILD ID':<38} {'STATUS':<12} {'START TIME':<25} {'DURATION':<15}")
    print("-" * 100)

    # Rows
    for build in builds:
        build_id = build.get("id", "N/A")
        status = build.get("status", "UNKNOWN")
        start_time = build.get("startTime", "")
        finish_time = build.get("finishTime", "")

        # Format status with color
        status_formatted = format_status(status, "workflow")

        # Calculate padding needed for status (12 chars minus visible status length)
        # ANSI color codes are invisible, so we need to pad based on actual status text
        status_padding = 12 - len(status)
        status_with_padding = status_formatted + " " * status_padding

        # Format timestamp
        start_formatted = format_timestamp_full(start_time) if start_time else "N/A"

        # Calculate duration
        if start_time and finish_time:
            duration = format_duration(start_time, finish_time)
        elif start_time:
            # Ongoing build - show elapsed time
            duration = format_duration(start_time, datetime.now().isoformat())
        else:
            duration = "N/A"

        # Print with proper spacing
        print(f"{build_id:<38} {status_with_padding} {start_formatted:<25} {duration:<15}")

    print()
    info(f"Showing {len(builds)} build(s) (use --limit to adjust)")
    print()


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
    project_root : Path
        Project root directory

    Returns
    -------
    int
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

    Parameters
    ----------
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
    project_root : Path
        Project root directory

    Returns
    -------
    int
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
    project_root : Path
        Project root directory

    Returns
    -------
    int
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
