# epycloud Reference

Complete reference for the `epycloud` command-line interface.

## Overview

The `epycloud` CLI provides a user-friendly interface for managing serverless epidemic modeling pipelines (epymodlingsuite) on Google Cloud. It supports:

- **Managing** cloud infrastructure with Terraform
- **Building** Docker images for pipeline execution
- **Running** workflows and individual pipeline stages
- **Monitoring** execution status and viewing logs
- **Validating** experiment configurations

## Usage

```console
$ epycloud [GLOBAL_OPTIONS] COMMAND [SUBCOMMAND] [OPTIONS] [ARGS]
```

## Global Options

These options can be used with any command:

| Option | Description | Default |
|--------|-------------|---------|
| `-h, --help` | Show help message | - |
| `-v, --version` | Show version | - |
| `-e, --env ENV` | Environment: dev/prod/local | `dev` |
| `--profile PROFILE` | Override active profile | From `active_profile` file |
| `-c, --config PATH` | Config file path | `~/.config/epymodelingsuite-cloud/config.yaml` |
| `-d, --project-dir PATH` | Project directory | Current directory |
| `--verbose` | Verbose output | Off |
| `--quiet` | Quiet mode | Off |
| `--dry-run` | Show what would happen without executing | Off |
| `--no-color` | Disable colored output | Off |

### Examples

```console
$ epycloud --env=prod workflow list

$ epycloud --profile=covid build cloud

$ epycloud --dry-run run workflow --exp-id test-experiment

$ epycloud --verbose logs --exp-id test
```

## Commands Summary

### Configuration & Setup

| Command | Description | Page |
|---------|-------------|------|
| [`config`](config.md) | Manage configuration files and settings | [→](config.md) |
| [`profile`](profile.md) | Manage project/disease-specific profiles | [→](profile.md) |
| [`validate`](validate.md) | Validate experiment configurations | [→](validate.md) |

### Building & Deployment

| Command | Description | Page |
|---------|-------------|------|
| [`build`](build.md) | Build Docker images for pipeline execution | [→](build.md) |
| [`terraform`](terraform.md) | Manage Google Cloud infrastructure | [→](terraform.md) |

### Running Workflows

| Command | Description | Page |
|---------|-------------|------|
| [`run`](run.md) | Execute workflows or individual pipeline stages | [→](run.md) |
| [`workflow`](workflow.md) | Manage workflow executions | [→](workflow.md) |

### Monitoring & Debugging

| Command | Description | Page |
|---------|-------------|------|
| [`status`](status.md) | Monitor active workflows and batch jobs | [→](status.md) |
| [`logs`](logs.md) | View and stream logs from pipeline runs | [→](logs.md) |

### Data & Results

| Command | Description | Page |
|---------|-------------|------|
| [`experiment`](experiment.md) | Browse experiments and runs on GCS | [→](experiment.md) |
| [`download`](download.md) | Download output plots from GCS | [→](download.md) |

## Common Workflows

### First-Time Setup

```console
$ epycloud config init

$ epycloud config edit

$ epycloud config edit-secrets

$ epycloud profile use flu

$ epycloud config show
```

### Development Workflow

```console
$ epycloud build dev

$ epycloud run workflow --exp-id test-sim --local

$ epycloud logs --exp-id test-sim
```

### Production Workflow

```console
$ epycloud --env=prod build cloud

$ epycloud build status

$ epycloud --env=prod run workflow --exp-id prod-study

$ epycloud workflow list --exp-id prod-study

$ epycloud logs --exp-id prod-study --follow
```

### Debugging Workflow

```console
$ epycloud run job --local --stage builder --exp-id test

$ epycloud run job --local --stage runner --exp-id test --run-id <id> --task-index 0

$ epycloud --verbose logs --exp-id test --tail 500
```

## Environment Variables

epycloud respects the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `EPYCLOUD_CONFIG_DIR` | Configuration directory path | `~/.config/epymodelingsuite-cloud` |
| `EPYCLOUD_ENV` | Default environment | `dev` |
| `EPYCLOUD_PROFILE` | Default profile | From `active_profile` file |
| `EDITOR` | Editor for config files | `vim` or `nano` |
| `NO_COLOR` | Disable colored output | Not set |

### Examples

```console
$ export EPYCLOUD_CONFIG_DIR=~/my-configs
$ epycloud config show

$ export EPYCLOUD_ENV=prod
$ epycloud workflow list

$ export EDITOR=code
$ epycloud config edit
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Configuration error |
| `3` | Validation error |
| `4` | Authentication error |
| `5` | Resource not found |

## Getting Help

For command-specific help:

```console
$ epycloud --help

$ epycloud config --help

$ epycloud config show --help
```

## See Also

- **[Quick Start Guide](../getting-started/local.md)**: Get started with epycloud
- **[Configuration Guide](../user-guide/configuration.md)**: Detailed configuration documentation
- **[User Guide](../user-guide/index.md)**: Comprehensive usage guide
- **[Troubleshooting](../user-guide/troubleshooting.md)**: Common issues and solutions
