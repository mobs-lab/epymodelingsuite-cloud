# epycloud status

Monitor active workflows and Cloud Batch jobs in real-time.

## Usage

```bash
epycloud status [OPTIONS]
```

## Description

Provides a real-time overview of active workflows and Cloud Batch jobs. The `TASKS` column shows completed work, while `SLOTS` shows occupied capacity against current demand. A separate provisioning warning identifies jobs that remain underfilled. Supports watch mode for continuous monitoring.

## Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--exp-id ID` | Optional | Filter by experiment ID | All experiments |
| `--watch`, `-w` | Flag | Watch mode - auto-refresh at interval | Disabled |
| `--recent [TIME]`, `-r` | Optional | Show recently completed items | 1 hour when present |
| `--interval N` | Optional | Refresh interval in seconds (with `--watch`) | 10 |
| `--stall-threshold MINUTES` | Optional | Warn after provisioning makes no progress for this long | 15 |

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

# Use a 25-minute provisioning grace period
epycloud status --watch --stall-threshold 25
```

In one-shot mode, a never-started job can be timed from its creation time. A partially filled job is reported as underfilled with an unknown duration because one snapshot cannot establish when progress stopped. Watch mode retains count history and reports a stall only after neither completed tasks nor occupied slots have changed for the threshold. Provisioning warnings do not change the successful exit code.

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
