# epycloud experiment

Browse experiments and runs stored in Google Cloud Storage.

## Usage

```bash
epycloud experiment SUBCOMMAND [OPTIONS]
```

## Subcommands

### list

List experiments and runs from GCS.

```bash
epycloud experiment list [OPTIONS]
```

#### Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `-e, --exp-filter PATTERN` | Optional | Glob pattern to filter experiment paths (fnmatch) | All experiments |
| `--latest` | Flag | Show only the latest run per experiment | Disabled |
| `-n, --limit N` | Optional | Number of rows to show (0 for all) | 50 |
| `--format {table,uri,args}` | Optional | Output format | `table` |
| `--bucket BUCKET` | Optional | GCS bucket name | From config |
| `--dir-prefix PREFIX` | Optional | GCS directory prefix | From config |

#### Output Formats

- **`table`** (default): Formatted table with timestamp, experiment ID, run ID, and a `*` marker for experiments with multiple runs.
- **`uri`**: One `gs://` URI per line, suitable for piping to other tools.
- **`args`**: `--exp-id` and `--run-id` flags per line, ready to copy-paste into other epycloud commands.

#### Examples

```bash
# List all experiments (default: 50 most recent)
epycloud experiment list

# Filter by pattern
epycloud experiment list -e "202607/*"
epycloud experiment list -e "*smc*"

# Show only latest run per experiment
epycloud experiment list --latest

# Show all runs (no limit)
epycloud experiment list -n 0

# Output as gs:// URIs for scripting
epycloud experiment list --format uri

# Output as CLI flags for copy-pasting
epycloud experiment list --format args

# Pipe-friendly: URIs on stdout, progress on stderr
epycloud experiment list --format uri 2>/dev/null

# Suppress progress messages entirely
epycloud -q experiment list --format uri
```

#### Example Output

**`--format table`** (default):

```bash
epycloud experiment list
```

```
 TIMESTAMP (EST)      EXPERIMENT ID    RUN ID
 2026-02-18 09:30:15  202607/exp1      20260218-143015-a1b2c3d4       *
 2026-02-17 14:00:00  202607/exp2      20260217-190000-def67890
 2026-02-16 10:45:22  202607/exp1      20260216-154522-ghi11111       *
```

Experiments with multiple runs are marked with `*`.

**`--format uri`**:

```bash
epycloud experiment list --format uri
```

```
gs://my-bucket/pipeline/flu/202607/exp1/20260218-143015-a1b2c3d4/
gs://my-bucket/pipeline/flu/202607/exp2/20260217-190000-def67890/
gs://my-bucket/pipeline/flu/202607/exp1/20260216-154522-ghi11111/
```

**`--format args`**:

```bash
epycloud experiment list --format args
```

```
--exp-id 202607/exp1 --run-id 20260218-143015-a1b2c3d4
--exp-id 202607/exp2 --run-id 20260217-190000-def67890
--exp-id 202607/exp1 --run-id 20260216-154522-ghi11111
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (API failure, GCS error) |
| `2` | Configuration error |

## Related Commands

- [`epycloud download`](download.md) - Download output files from experiments
- [`epycloud workflow list`](workflow.md#list) - List workflow executions
- [`epycloud logs`](logs.md) - View pipeline logs
