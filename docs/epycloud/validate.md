# epycloud validate

Validate experiment configuration files before running workflows.

## Usage

```bash
epycloud validate --exp-id EXP_ID [OPTIONS]
epycloud validate --path PATH [OPTIONS]
```

## Description

Validates experiment configuration files before submitting workflows. Fetches YAML configurations from GitHub or reads from local path, then validates using `epymodelingsuite` loaders to catch configuration errors early.

## Options

| Option | Type | Description | Required |
|--------|------|-------------|----------|
| `--exp-id ID` | String | Experiment ID from GitHub experiment repository | Either --exp-id or --path |
| `--path PATH` | String | Local path to configuration directory | Either --exp-id or --path |
| `--format FORMAT` | String | Output format: `text`, `json`, `yaml` | No (default: text) |
| `--github-token TOKEN` | String | GitHub PAT (overrides config) | No |
| `--strict` | Flag | Treat warnings as errors | No |

## Examples

```bash
# Validate from GitHub
epycloud validate --exp-id flu-2024

# Validate local configuration
epycloud validate --path ./local/forecast/experiments/test-sim/config

# JSON output for automation
epycloud validate --exp-id flu-2024 --format json

# Strict mode (warnings as errors)
epycloud validate --exp-id flu-2024 --strict

# Validate with explicit token
epycloud validate --exp-id flu-2024 --github-token ghp_xxxxx

# Pre-flight check before workflow
epycloud validate --exp-id flu-2024 && epycloud run workflow --exp-id flu-2024
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Validation passed |
| `1` | Validation failed (configuration errors) |
| `2` | Configuration error (cannot access configs) |

## Related Commands

- [`epycloud run workflow`](run.md#run-workflow) - Submit validated workflow
- [`epycloud config`](config.md) - Manage GitHub token and repository settings

## See Also

- [Configuration Guide](../user-guide/configuration.md) - Configuration system
- [Running Experiments](../user-guide/running-experiments/) - Experiment execution
- [Troubleshooting](../user-guide/troubleshooting.md) - Debug configuration errors
