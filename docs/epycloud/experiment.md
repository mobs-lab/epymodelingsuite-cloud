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
| `--format {table,uri}` | Optional | Output format | `table` |
| `--bucket BUCKET` | Optional | GCS bucket name | From config |
| `--dir-prefix PREFIX` | Optional | GCS directory prefix | From config |

#### Output Formats

- **`table`** (default): Displays a formatted table with timestamp, experiment ID, run ID, and a `*` marker for experiments with multiple runs.
- **`uri`**: Prints one `gs://` URI per line, suitable for piping to other tools.

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

# Pipe-friendly: URIs on stdout, progress on stderr
epycloud experiment list --format uri 2>/dev/null

# Suppress progress messages entirely
epycloud -q experiment list --format uri
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
