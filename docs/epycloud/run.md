# epycloud run

Execute workflows or individual pipeline stages.

## Usage

```bash
epycloud run SUBCOMMAND [OPTIONS]
```

## Description

Executes pipeline workflows and jobs. Supports two execution modes:

- **Workflows** - Orchestrate all three stages (Builder → Runner → Output) via Cloud Workflows
- **Jobs** - Run individual stages or tasks for debugging and testing

Both cloud and local execution are supported.

## Subcommands

### workflow

Submit a complete workflow.

```bash
epycloud run workflow --exp-id EXP_ID [OPTIONS]
```

**Required:**

- `--exp-id ID` - Experiment identifier

**Options:**

- `--run-id ID` - Run identifier (auto-generated if not provided)
- `--local` - Run locally with Docker Compose
- `--skip-output` - Skip Stage C (output generation)
- `--max-parallelism N` - Override max parallel tasks for Stage B
- `--stage-a-machine-type TYPE` - Override Stage A machine type (auto-sets CPU/memory to machine max)
- `--stage-b-machine-type TYPE` - Override Stage B machine type (auto-sets CPU/memory to machine max)
- `--stage-c-machine-type TYPE` - Override Stage C machine type (auto-sets CPU/memory to machine max)
- `--task-count-per-node N` - Max tasks per VM node (1 = dedicated VM per task)
- `--forecast-repo-ref REF` - Override experiment repo branch/tag/commit
- `--wait` - Wait for completion and stream logs
- `--yes` - Auto-confirm without prompting
- `--dry-run` - Show what would happen without executing
- `--project-directory DIR` - Docker Compose project directory (default: auto-detected)
- `--output-config FILE` - Specify output config for Stage C (e.g., output_projection.yaml)

**Cloud execution (default):**
Submits to Google Cloud Workflows. Returns execution ID immediately.

**Local execution (`--local`):**
Uses Docker Compose. Requires experiment repository in `./local/forecast/`.

### job

Run individual pipeline stage or task.

```bash
epycloud run job --stage STAGE [OPTIONS]
```

**Required:**

- `--stage STAGE` - Stage: `A`, `B`, `C`, `builder`, `runner`, `output`
- `--exp-id ID` - Experiment identifier

**Options:**

- `--run-id ID` - Run identifier (required for stages B and C, auto-generated for stage A)
- `--task-index N` - Task index for Stage B (default: 0)
- `--num-tasks N` - Number of tasks (required for Stage C)
- `--machine-type TYPE` - Override machine type for this job (auto-sets CPU/memory to machine max)
- `--task-count-per-node N` - Max tasks per VM node (1 = dedicated VM per task)
- `--local` - Run locally with Docker Compose
- `--wait` - Wait for completion and stream logs
- `--yes` - Auto-confirm without prompting
- `--dry-run` - Show what would happen without executing
- `--project-directory DIR` - Docker Compose project directory (default: auto-detected)
- `--output-config FILE` - Output config for Stage C (e.g., output_projection.yaml)

**Cloud execution:**
Submits individual Cloud Batch job.

**Local execution:**
Runs stage in Docker Compose.

## Examples

### Cloud Workflows

```bash
# Submit workflow
epycloud run workflow --exp-id flu-2024

# Submit with custom run ID
epycloud run workflow --exp-id flu-2024 --run-id 20250109-custom

# Submit and wait for completion
epycloud run workflow --exp-id flu-2024 --wait

# Skip output generation
epycloud run workflow --exp-id flu-2024 --skip-output

# Override parallelism
epycloud run workflow --exp-id flu-2024 --max-parallelism 50

# Use specific machine types
epycloud run workflow --exp-id flu-2024 --stage-b-machine-type n2-highmem-8

# Override experiment repository branch
epycloud run workflow --exp-id flu-2024 --forecast-repo-ref develop

# Dry run (show what would happen)
epycloud run workflow --exp-id flu-2024 --dry-run
```

### Local Workflows

```bash
# Run complete workflow locally
epycloud run workflow --exp-id test-sim --local
```

### Cloud Jobs

```bash
# Run Stage A (builder)
epycloud run job --stage A --exp-id flu-2024

# Run Stage B task (runner)
epycloud run job --stage B --exp-id flu-2024 --run-id 20250109-abc123 --task-index 0

# Run Stage C (output)
epycloud run job --stage C --exp-id flu-2024 --run-id 20250109-abc123 --num-tasks 100

# Run Stage B with custom machine type
epycloud run job --stage B --exp-id flu-2024 --run-id 20250109-abc123 --task-index 0 --machine-type n2-highmem-8
```

### Local Jobs

```bash
# Run Stage A locally
epycloud run job --local --stage builder --exp-id test-sim

# Run Stage B task locally
epycloud run job --local --stage runner --exp-id test-sim --run-id 20250109-abc123 --task-index 0

# Run Stage C locally
epycloud run job --local --stage output --exp-id test-sim --run-id 20250109-abc123 --num-tasks 2

# Run Stage C with specific output config
epycloud run job --local --stage output --exp-id test-sim --run-id 20250109-abc123 --num-tasks 2 --output-config output_projection.yaml
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success (job submitted or completed) |
| `1` | Error (invalid options, submission failed) |

## Related Commands

- [`epycloud workflow list`](workflow.md#list) - List workflow executions
- [`epycloud logs`](logs.md) - View execution logs
- [`epycloud status`](status.md) - Monitor execution status

## See Also

- [Running Experiments](../user-guide/running-experiments/) - Detailed experiment execution
- [Local Development](../user-guide/local-development.md) - Local testing workflow
- [Pipeline Stages](../architecture/pipeline-stages.md) - Stage architecture
