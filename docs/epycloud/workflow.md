# epycloud workflow

Manage Google Cloud Workflows executions.

## Usage

```bash
epycloud workflow SUBCOMMAND [OPTIONS]
```

## Description

Provides tools for managing Cloud Workflows executions. Monitor pipeline runs, view execution details, stream logs, and cancel running workflows. Cloud Workflows orchestrates the three-stage pipeline (Builder → Runners → Output).

## Subcommands

### list

List workflow executions with optional filtering.

```bash
epycloud workflow list [OPTIONS]
```

**Options:**
- `--limit N` - Number of executions to show (default: 20)
- `--status STATUS` - Filter by status: ACTIVE, SUCCEEDED, FAILED, CANCELLED
- `--exp-id ID` - Filter by experiment ID
- `--since DURATION` - Show executions since (e.g., 24h, 7d)

### describe

Show detailed information about a workflow execution.

```bash
epycloud workflow describe EXECUTION_ID
```

### logs

View or stream logs from a workflow execution.

```bash
epycloud workflow logs EXECUTION_ID [OPTIONS]
```

**Options:**
- `--follow`, `-f` - Stream logs in real-time
- `--tail N` - Show last N log entries (default: 100)
- `--level LEVEL` - Filter by log level

!!! note "Workflow vs Pipeline Logs"
    - `epycloud workflow logs` - Orchestration logs (workflow steps, job submissions)
    - `epycloud logs` - Pipeline execution logs (builder, runner, output scripts)

### cancel

Cancel a running workflow execution.

```bash
epycloud workflow cancel EXECUTION_ID [OPTIONS]
```

**Options:**
- `--only-workflow` - Cancel only workflow, not batch jobs

**Default behavior:** Cancels workflow and all child batch jobs (cascade).

### retry

Retry a failed workflow execution.

```bash
epycloud workflow retry EXECUTION_ID
```

Reuses same parameters and `RUN_ID` from original execution.

## Examples

```bash
# List 20 most recent executions
epycloud workflow list

# List 50 most recent
epycloud workflow list --limit 50

# Filter by experiment ID
epycloud workflow list --exp-id flu-2024

# Filter by status
epycloud workflow list --status FAILED

# Show executions from last 24 hours
epycloud workflow list --since 24h

# Describe execution details
epycloud workflow describe abc123-def456-ghi789

# View workflow logs
epycloud workflow logs abc123-def456-ghi789

# Stream logs in real-time
epycloud workflow logs abc123-def456-ghi789 --follow

# View last 500 entries
epycloud workflow logs abc123-def456-ghi789 --tail 500

# Cancel workflow and batch jobs
epycloud workflow cancel abc123-def456-ghi789

# Cancel only workflow, preserve jobs
epycloud workflow cancel abc123-def456-ghi789 --only-workflow

# Retry failed workflow
epycloud workflow retry abc123-def456-ghi789
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (execution not found, API failure) |

## Related Commands

- [`epycloud run workflow`](run.md#run-workflow) - Submit new workflow
- [`epycloud status`](status.md) - Monitor active workflows and batch jobs
- [`epycloud logs`](logs.md) - View pipeline logs

## See Also

- [Running Experiments](../user-guide/running-experiments/) - Complete experiment guide
- [Monitoring Guide](../user-guide/monitoring.md) - Monitoring strategies
- [Troubleshooting](../user-guide/troubleshooting.md) - Debug workflow issues
