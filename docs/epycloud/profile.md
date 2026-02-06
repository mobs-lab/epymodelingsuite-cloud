# epycloud profile

Manage disease/project-specific configuration profiles.

## Usage

```bash
epycloud profile SUBCOMMAND [OPTIONS]
```

## Description

Manages disease or project-specific configuration profiles (flu, COVID-19, RSV, etc.). Profiles allow maintaining separate settings for different projects without modifying base configuration. Settings include experiment repository paths, default resource allocations, and project-specific configurations.

## Subcommands

### list

List all available profiles.

```bash
epycloud profile list
```

### current

Show the currently active profile.

```bash
epycloud profile current
```

### use

Activate a specific profile.

```bash
epycloud profile use PROFILE
```

### create

Create a new profile.

```bash
epycloud profile create NAME [OPTIONS]
```

**Options:**
- `--from PROFILE` - Copy settings from existing profile
- `--template TEMPLATE` - Use predefined template (flu, covid, rsv)

### edit

Edit profile configuration.

```bash
epycloud profile edit PROFILE
```

### show

Display profile details.

```bash
epycloud profile show PROFILE
```

### delete

Delete a profile.

```bash
epycloud profile delete PROFILE [--force]
```

## Examples

```bash
# List all profiles
epycloud profile list

# Show active profile
epycloud profile current

# Activate flu profile
epycloud profile use flu

# Create new profile from template
epycloud profile create mpox --template rsv

# Create test profile from existing
epycloud profile create flu-test --from flu

# Edit profile
epycloud profile edit flu

# Show profile details
epycloud profile show flu

# Delete profile
epycloud profile delete old-experiment
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (profile not found, validation failed) |

## Related Commands

- [`epycloud config`](config.md) - Base configuration management
- [`epycloud config show`](config.md#show) - View merged configuration with active profile

## See Also

- [Configuration Guide](../user-guide/configuration.md) - Configuration system and profiles
- [Getting Started](../getting-started/index.md) - Initial setup with profiles
