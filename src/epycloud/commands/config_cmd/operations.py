"""Config operations (initialization, file management)."""

import os
import shutil
import subprocess
from pathlib import Path

import yaml

from epycloud.execution.gcp_machines import get_candidate_chain
from epycloud.lib.output import ask_confirmation, error, info, status, success, warning
from epycloud.lib.paths import (
    get_config_dir,
    get_config_file,
    get_environment_file,
    get_secrets_file,
)


def initialize_config_dir() -> int:
    """Initialize config directory with templates.

    Returns
    -------
    int
        Exit code
    """
    config_dir = get_config_dir()
    template_dir = Path(__file__).parent.parent.parent / "config" / "templates"

    status(f"Initializing config directory: {config_dir}")

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "environments").mkdir(exist_ok=True)
    (config_dir / "profiles").mkdir(exist_ok=True)

    # Copy templates
    templates = [
        ("config.yaml", config_dir / "config.yaml"),
        ("dev.yaml", config_dir / "environments" / "dev.yaml"),
        ("staging.yaml", config_dir / "environments" / "staging.yaml"),
        ("prod.yaml", config_dir / "environments" / "prod.yaml"),
        ("local.yaml", config_dir / "environments" / "local.yaml"),
        ("flu.yaml", config_dir / "profiles" / "flu.yaml"),
        ("secrets.yaml", config_dir / "secrets.yaml"),
    ]

    for template_name, dest_path in templates:
        template_path = template_dir / template_name

        if dest_path.exists():
            warning(f"Skipping {dest_path.name} (already exists)")
            continue

        shutil.copy(template_path, dest_path)
        success(f"Created {dest_path.name}")

        # Set secrets file permissions
        if dest_path.name == "secrets.yaml":
            os.chmod(dest_path, 0o600)
            status("  Set permissions to 0600")

    # Set default profile
    active_profile_file = config_dir / "active_profile"
    if not active_profile_file.exists():
        active_profile_file.write_text("flu\n")
        success("Set default profile to 'flu'")

    print()  # Blank line before
    success(f"Configuration initialized at {config_dir}")
    print()  # Blank line before
    info("Next steps:")
    info("  1. Edit config.yaml with your GCP project settings")
    info("  2. Add your GitHub token to secrets.yaml")
    info("  3. Review environment configs in environments/")
    info("  4. Run 'epycloud config validate' to check configuration")

    return 0


def _migrate_stage_block(stage: str, stage_config: dict) -> tuple[dict, bool, str | None]:
    """Return one stage block with a requirement-based candidate chain."""
    if "machine_types" in stage_config:
        if "machine_type" not in stage_config:
            return stage_config, False, None
        return (
            {key: value for key, value in stage_config.items() if key != "machine_type"},
            True,
            None,
        )
    if "machine_type" not in stage_config:
        return stage_config, False, None

    migrated = dict(stage_config)
    machine_type = migrated.get("machine_type")
    if not isinstance(machine_type, str):
        return stage_config, False, "machine_type must be a string"

    # Correct defaults that represented the selected VM maximum rather than
    # the workload minimum. These exact legacy values shipped with epycloud.
    if stage in ("a", "b") and machine_type == "c4d-standard-2":
        if migrated.get("cpu_milli", 2000) == 2000 and migrated.get("memory_mib") == 8192:
            migrated["memory_mib"] = 7168
    if stage == "c" and machine_type == "c4d-standard-8":
        if migrated.get("cpu_milli") == 8000 and migrated.get("memory_mib") == 31744:
            migrated["cpu_milli"] = 4000

    defaults = {
        "a": (2000, 7168),
        "b": (2000, 7168),
        "c": (4000, 15360),
    }
    default_cpu, default_memory = defaults[stage]
    min_cpu = migrated.get("cpu_milli", default_cpu)
    min_memory = migrated.get("memory_mib", default_memory)
    if (
        isinstance(min_cpu, bool)
        or not isinstance(min_cpu, int)
        or isinstance(min_memory, bool)
        or not isinstance(min_memory, int)
    ):
        return stage_config, False, "cpu_milli and memory_mib must be integers"

    chain = get_candidate_chain(min_cpu, min_memory)
    if not chain:
        return (
            stage_config,
            False,
            f"no maintained chain satisfies {min_cpu} mCPU and {min_memory} MiB",
        )

    result = {}
    for key, value in migrated.items():
        if key == "machine_type":
            result["machine_types"] = list(chain)
        else:
            result[key] = value
    return result, True, None


def _write_yaml_atomically(path: Path, content: dict) -> None:
    """Replace a YAML file atomically while preserving its permission bits."""
    mode = path.stat().st_mode & 0o777
    temp_path: Path | None = None
    try:
        for index in range(100):
            candidate = path.with_name(f".{path.name}.{os.getpid()}.{index}.tmp")
            try:
                handle = candidate.open("x")
                temp_path = candidate
                with handle:
                    yaml.safe_dump(content, handle, default_flow_style=False, sort_keys=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                break
            except FileExistsError:
                continue
        if temp_path is None:
            raise OSError(f"Unable to create a temporary file next to {path}")
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def migrate_machine_type_chains(config_dir: Path | None = None) -> int:
    """Migrate legacy stage machine types in base, environment, and profile files."""
    config_dir = config_dir or get_config_dir()
    config_file = (
        get_config_file() if config_dir == get_config_dir() else config_dir / "config.yaml"
    )
    if not config_file.exists():
        error("Config file not found. Run 'epycloud config init' first.")
        return 1

    paths = [config_file]
    for subdirectory in ("environments", "profiles"):
        directory = config_dir / subdirectory
        if directory.exists():
            paths.extend(sorted(directory.glob("*.yaml")))
            paths.extend(sorted(directory.glob("*.yml")))

    planned: dict[Path, dict] = {}
    failures: list[str] = []
    for path in paths:
        try:
            content = yaml.safe_load(path.read_text()) or {}
        except (OSError, yaml.YAMLError) as exc:
            failures.append(f"{path}: {exc}")
            continue
        batch = content.get("google_cloud", {}).get("batch")
        if not isinstance(batch, dict):
            continue

        changed = False
        for stage in ("a", "b", "c"):
            key = f"stage_{stage}"
            stage_config = batch.get(key)
            if not isinstance(stage_config, dict):
                continue
            migrated, stage_changed, failure = _migrate_stage_block(stage, stage_config)
            if failure:
                failures.append(f"{path}: {key}: {failure}")
                continue
            if stage_changed:
                batch[key] = migrated
                changed = True
        if changed:
            planned[path] = content

    if failures:
        error("Configuration migration failed; no files were changed:")
        for failure in failures:
            error(f"  - {failure}")
        return 1

    if not planned:
        success("Configuration is already migrated")
        return 0

    for path, content in planned.items():
        backup = path.with_suffix(path.suffix + ".pre-machine-chains.bak")
        if not backup.exists():
            shutil.copy2(path, backup)
        _write_yaml_atomically(path, content)
        success(f"Migrated {path}")
        info(f"  Backup: {backup}")

    success("Machine fallback chain migration complete")
    return 0


def _open_file_in_editor(file_path: Path, file_description: str) -> int:
    """Open file in editor with user confirmation.

    Parameters
    ----------
    file_path : Path
        Path to file to edit
    file_description : str
        Human-readable description (e.g., "config file", "secrets file")

    Returns
    -------
    int
        Exit code (0 for success, 1 for failure/skip)
    """
    # 1. Get editor name
    editor = os.environ.get("EDITOR", "vim")

    # 2. Check if editor exists
    editor_path = shutil.which(editor)
    if not editor_path:
        # Editor not found - show instructions
        warning(f"Editor '{editor}' not found.")
        print()
        info(f"{file_description.capitalize()} location:")
        info(f"  {file_path}")
        print()
        info("You can edit this file with your preferred editor:")
        info(f"  nano {file_path}")
        info(f"  code {file_path}")
        print()
        info("Or set EDITOR environment variable:")
        info("  export EDITOR=nano")
        return 1

    # 3. Prompt user for confirmation
    if not ask_confirmation(f"Edit {file_description} in {editor}?", default=False):
        # User declined - show path for manual editing
        print()
        info(f"{file_description.capitalize()} location:")
        info(f"  {file_path}")
        print()
        info("You can edit this file with your preferred editor:")
        info(f"  {editor} {file_path}")
        info(f"  nano {file_path}")
        info(f"  code {file_path}")
        print()
        info("Or set EDITOR environment variable:")
        info(f"  export EDITOR={editor}")
        return 0  # Not an error - user chose not to edit

    # 4. Open in editor
    try:
        subprocess.run([editor, str(file_path)], check=True)
        success(f"Edited {file_path}")
        return 0
    except subprocess.CalledProcessError as e:
        error(f"Editor failed: {e}")
        return 1


def edit_config_file(env: str | None = None) -> int:
    """Edit config file in $EDITOR.

    Parameters
    ----------
    env : str | None
        Environment name to edit (None = base config)

    Returns
    -------
    int
        Exit code
    """
    # Determine which file to edit
    if env:
        file_path = get_environment_file(env)
        if not file_path.exists():
            error(f"Environment config not found: {file_path}")
            return 1
        description = f"{env} environment config"
    else:
        # Default: edit base config.yaml
        file_path = get_config_file()
        if not file_path.exists():
            error(f"Config file not found: {file_path}")
            info("Run 'epycloud config init' first")
            return 1
        description = "config file"

    return _open_file_in_editor(file_path, description)


def edit_secrets_file() -> int:
    """Edit secrets.yaml file in $EDITOR.

    Returns
    -------
    int
        Exit code
    """
    file_path = get_secrets_file()

    # Create secrets file with secure permissions if it doesn't exist
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            "# Secrets configuration\n"
            "# Store sensitive credentials here\n\n"
            "github:\n"
            '  personal_access_token: ""\n'
        )
        os.chmod(file_path, 0o600)
        status(f"Created {file_path} with secure permissions (0600)")

    result = _open_file_in_editor(file_path, "secrets file")

    # Verify permissions after editing (only if file was actually edited)
    if result == 0 and file_path.exists():
        current_perms = file_path.stat().st_mode & 0o777
        if current_perms != 0o600:
            warning(f"Secrets file has insecure permissions: {oct(current_perms)}")
            status("Setting permissions to 0600...")
            os.chmod(file_path, 0o600)
            success("Permissions fixed")

    return result
