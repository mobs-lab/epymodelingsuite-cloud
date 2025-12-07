"""Handler functions for build subcommands."""

import json
import subprocess
import sys
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
from epycloud.lib.output import error, info

from . import cloud, dev, display, local


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
        return handle_cloud(ctx)
    elif args.build_subcommand == "local":
        return handle_local(ctx)
    elif args.build_subcommand == "dev":
        return handle_dev(ctx)
    elif args.build_subcommand == "status":
        return handle_status(ctx)

    # Should never reach here
    error(f"Unknown build subcommand: {args.build_subcommand}")
    return 1


def handle_cloud(ctx: dict[str, Any]) -> int:
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
    docker_config = get_docker_config(config)
    image_tag = args.tag or docker_config["image_tag"]
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
    project_root = get_project_root().resolve()

    # Resolve dockerfile and context paths
    dockerfile = getattr(args, "dockerfile", None)
    context = getattr(args, "context", None)

    if dockerfile:
        dockerfile_path = Path(dockerfile).resolve()
    else:
        dockerfile_path = (project_root / "docker" / "Dockerfile").resolve()

    if context:
        context_path = Path(context).resolve()
    else:
        context_path = project_root.resolve()

    return cloud.build_cloud(
        project_id=project_id,
        region=region,
        repo_name=docker_config["repo_name"],
        image_name=docker_config["image_name"],
        image_tag=image_tag,
        image_path=image_path,
        modeling_suite_repo=modeling_suite_repo,
        modeling_suite_ref=modeling_suite_ref,
        no_cache=not args.cache,  # Inverted: --cache flag enables cache, default is no cache
        wait=args.wait,
        verbose=verbose,
        dry_run=dry_run,
        dockerfile_path=dockerfile_path,
        context_path=context_path,
    )


def handle_local(ctx: dict[str, Any]) -> int:
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
    docker_config = get_docker_config(config)
    image_tag = args.tag or docker_config["image_tag"]
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
    project_root = get_project_root().resolve()

    # Resolve dockerfile and context paths
    dockerfile = getattr(args, "dockerfile", None)
    context = getattr(args, "context", None)

    if dockerfile:
        dockerfile_path = Path(dockerfile).resolve()
    else:
        dockerfile_path = (project_root / "docker" / "Dockerfile").resolve()

    if context:
        context_path = Path(context).resolve()
    else:
        context_path = project_root.resolve()

    return local.build_local(
        image_path=image_path,
        modeling_suite_repo=modeling_suite_repo,
        modeling_suite_ref=modeling_suite_ref,
        github_pat=github_pat,
        no_cache=args.no_cache,
        push=not args.no_push,
        verbose=verbose,
        dry_run=dry_run,
        dockerfile_path=dockerfile_path,
        context_path=context_path,
    )


def handle_dev(ctx: dict[str, Any]) -> int:
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
    docker_config = get_docker_config(config)
    image_name = docker_config["image_name"]
    # Default to "local" for dev builds (matches docker-compose.yml)
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
    project_root = get_project_root().resolve()

    # Resolve dockerfile and context paths
    dockerfile = getattr(args, "dockerfile", None)
    context = getattr(args, "context", None)

    if dockerfile:
        dockerfile_path = Path(dockerfile).resolve()
    else:
        dockerfile_path = (project_root / "docker" / "Dockerfile").resolve()

    if context:
        context_path = Path(context).resolve()
    else:
        context_path = project_root.resolve()

    return dev.build_dev(
        image_name=image_name,
        image_path=image_path,
        modeling_suite_repo=modeling_suite_repo,
        modeling_suite_ref=modeling_suite_ref,
        github_pat=github_pat,
        no_cache=args.no_cache,
        push=args.push,
        verbose=verbose,
        dry_run=dry_run,
        dockerfile_path=dockerfile_path,
        context_path=context_path,
    )


def handle_status(ctx: dict[str, Any]) -> int:
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
        display.display_build_status(builds, args.limit)

        return 0

    except json.JSONDecodeError as e:
        error(f"Failed to parse gcloud output: {e}")
        if verbose:
            print(result.stdout, file=sys.stderr)
        return 1
    except Exception as e:
        error(f"Unexpected error: {e}")
        return 1
