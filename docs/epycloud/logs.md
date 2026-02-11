# epycloud logs

View and stream logs from Cloud Batch jobs.

## Usage

```bash
epycloud logs --exp-id EXP_ID [OPTIONS]
```

## Description

Retrieve pipeline execution logs from Google Cloud Logging. View and stream logs from Cloud Batch jobs, filter by stage, task, severity level, or time range.

!!! note "Pipeline Logs vs Workflow Logs"
    `epycloud logs` shows pipeline execution logs (builder, runner, output scripts). For orchestration logs, use [`epycloud workflow logs`](workflow.md#logs).

## Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--exp-id ID` | Required | Experiment ID | - |
| `--run-id ID` | Optional | Filter by specific run ID | All runs |
| `--stage STAGE` | Optional | Filter by stage: `A`, `B`, `C`, `builder`, `runner`, `output` | All stages |
| `--task-index N` | Optional | Filter by task index (Stage B only) | All tasks |
| `--follow`, `-f` | Flag | Stream logs in real-time | Disabled |
| `--tail N` | Optional | Show last N log entries (0 = all) | 100 |
| `--since DURATION` | Optional | Show logs since duration (e.g., `1h`, `30m`, `2d`) | No limit |
| `--level LEVEL` | Optional | Filter by log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | All levels |

## Examples

```bash
# View last 100 logs
epycloud logs --exp-id flu-2024

# View all logs
epycloud logs --exp-id flu-2024 --tail 0

# Filter by stage
epycloud logs --exp-id flu-2024 --stage B

# View specific task
epycloud logs --exp-id flu-2024 --stage B --task-index 42

# Stream logs in real-time
epycloud logs --exp-id flu-2024 --follow

# View only errors from last hour
epycloud logs --exp-id flu-2024 --level ERROR --since 1h

# Export to file
epycloud --no-color logs --exp-id flu-2024 --tail 0 > logs.txt
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (invalid options, API failure, no logs found) |

## Related Commands

- [`epycloud workflow logs`](workflow.md#logs) - View workflow orchestration logs
- [`epycloud status`](status.md) - Monitor active workflows and jobs
- [`epycloud workflow list`](workflow.md#list) - List workflow executions

## See Also

- [Monitoring Guide](../user-guide/monitoring.md) - Monitoring strategies and troubleshooting
- [Google Cloud Logging](https://cloud.google.com/logging/docs)
