"""Config operations (initialization, file management)."""

import os
import shutil
import subprocess
from pathlib import Path

from epycloud.lib.output import info, success, warning
from epycloud.lib.paths import get_config_dir, get_config_file, get_environment_file, get_secrets_file


def initialize_config_dir() -> int:
    """Initialize config directory with templates.

    Returns
    -------
    int
        Exit code
    """
    config_dir = get_config_dir()
    template_dir = Path(__file__).parent.parent.parent / "config" / "templates"

    info(f"Initializing config directory: {config_dir}")

    # Create directories
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "environments").mkdir(exist_ok=True)
    (config_dir / "profiles").mkdir(exist_ok=True)

    # Copy templates
    templates = [
        ("config.yaml", config_dir / "config.yaml"),
        ("dev.yaml", config_dir / "environments" / "dev.yaml"),
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
            info("  Set permissions to 0600")

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
    editor = os.environ.get("EDITOR", "vim")

    # Determine which file to edit
    if env:
        file_path = get_environment_file(env)
        if not file_path.exists():
            from epycloud.lib.output import error

            error(f"Environment config not found: {file_path}")
            return 1
    else:
        # Default: edit base config.yaml
        file_path = get_config_file()
        if not file_path.exists():
            from epycloud.lib.output import error

            error(f"Config file not found: {file_path}")
            info("Run 'epycloud config init' first")
            return 1

    # Open in editor
    try:
        subprocess.run([editor, str(file_path)], check=True)
        success(f"Edited {file_path}")
        return 0
    except subprocess.CalledProcessError as e:
        from epycloud.lib.output import error

        error(f"Editor failed: {e}")
        return 1
    except FileNotFoundError:
        from epycloud.lib.output import error

        error(f"Editor not found: {editor}")
        info("Set EDITOR environment variable or use 'epycloud config show'")
        return 1


def edit_secrets_file() -> int:
    """Edit secrets.yaml file in $EDITOR.

    Returns
    -------
    int
        Exit code
    """
    editor = os.environ.get("EDITOR", "vim")
    file_path = get_secrets_file()

    # Create secrets file with secure permissions if it doesn't exist
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            '# Secrets configuration\n# Store sensitive credentials here\n\ngithub:\n  personal_access_token: ""\n'
        )
        os.chmod(file_path, 0o600)
        info(f"Created {file_path} with secure permissions (0600)")

    # Open in editor
    try:
        subprocess.run([editor, str(file_path)], check=True)
        success(f"Edited {file_path}")

        # Verify permissions after editing
        current_perms = file_path.stat().st_mode & 0o777
        if current_perms != 0o600:
            warning(f"Secrets file has insecure permissions: {oct(current_perms)}")
            info("Setting permissions to 0600...")
            os.chmod(file_path, 0o600)
            success("Permissions fixed")

        return 0
    except subprocess.CalledProcessError as e:
        from epycloud.lib.output import error

        error(f"Editor failed: {e}")
        return 1
    except FileNotFoundError:
        from epycloud.lib.output import error

        error(f"Editor not found: {editor}")
        info("Set EDITOR environment variable")
        return 1
