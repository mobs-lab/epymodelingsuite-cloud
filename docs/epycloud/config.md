# epycloud config

Manage epycloud configuration files.

## Usage

```bash
epycloud config SUBCOMMAND [OPTIONS]
```

## Description

Provides configuration management for epycloud. Supports initialization, validation, viewing, and editing of configuration files across multiple layers (base, environment, profile).

Configuration files are stored in `~/.config/epymodelingsuite-cloud/`.

## Subcommands

### init

Initialize configuration directory structure.

```bash
epycloud config init
```

Creates base configuration, environments, and profiles directories.

### show

Display current merged configuration.

```bash
epycloud config show [--raw]
```

**Options:**
- `--raw` - Show raw YAML

Shows merged configuration from all layers (base + environment + profile).

### edit

Edit base configuration file.

```bash
epycloud config edit
```

Opens configuration in `$EDITOR` (vim, nano, etc.).

### edit-secrets

Edit secrets configuration file.

```bash
epycloud config edit-secrets
```

Opens secrets file (GitHub PAT, etc.) in `$EDITOR`. File has 0600 permissions.

### validate

Validate configuration files.

```bash
epycloud config validate
```

Checks syntax and required fields across all configuration layers.

### path

Show configuration directory path.

```bash
epycloud config path
```

Prints path to configuration directory.

### get

Get specific configuration value.

```bash
epycloud config get KEY
```

**Arguments:**
- `KEY` - Dot-notation key (e.g., `google_cloud.project_id`)

### set

Set configuration value.

```bash
epycloud config set KEY VALUE
```

**Arguments:**
- `KEY` - Dot-notation key
- `VALUE` - Value to set

### list-envs

List available environments.

```bash
epycloud config list-envs
```

Shows all environment configuration files.

## Examples

```bash
# Initialize configuration
epycloud config init

# Show current configuration
epycloud config show

# Show raw YAML configuration
epycloud config show --raw

# Show configuration for production environment
epycloud --env prod config show

# Edit base configuration
epycloud config edit

# Edit secrets
epycloud config edit-secrets

# Validate all configurations
epycloud config validate

# Show config directory path
epycloud config path

# Get specific value
epycloud config get google_cloud.project_id
epycloud config get docker.image_tag

# Set value
epycloud config set docker.image_tag v2.0.0

# List environments
epycloud config list-envs
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (validation failed, file not found) |

## Related Commands

- [`epycloud profile`](profile.md) - Manage disease/project profiles

## See Also

- [Configuration Guide](../user-guide/configuration.md) - Configuration system details
- [Getting Started](../getting-started/installation.md) - Initial configuration setup
