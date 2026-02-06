# epycloud status

Monitor active workflows and Cloud Batch jobs in real-time.

## Usage

```bash
epycloud status [OPTIONS]
```

## Description

Provides a real-time overview of active workflows and Cloud Batch jobs. Displays current execution status, running workflow/jobs, and task progress. Supports watch mode for continuous monitoring.

## Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--exp-id ID` | Optional | Filter by experiment ID | All experiments |
| `--watch`, `-w` | Flag | Watch mode - auto-refresh at interval | Disabled |
| `--interval N` | Optional | Refresh interval in seconds (with `--watch`) | 10 |

## Examples

```bash
# Show status of all active workflows and jobs
epycloud status

# Show status for specific experiment
epycloud status --exp-id flu-2024

# Watch mode with default 10-second refresh
epycloud status --watch

# Watch with custom 5-second interval
epycloud status --watch --interval 5

```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (API failure, invalid options) |

## Related Commands

- [`epycloud workflow list`](workflow.md#list) - List workflow executions
- [`epycloud logs`](logs.md) - View pipeline logs
- [`epycloud workflow describe`](workflow.md#describe) - Detailed workflow info

## See Also

- [Monitoring Guide](../user-guide/monitoring.md) - Monitoring strategies and troubleshooting
- [Google Cloud Batch](https://cloud.google.com/batch/docs)
