# epycloud download

Download output plots from Google Cloud Storage.

## Usage

```bash
epycloud download [OPTIONS]
```

## Description

Downloads specific output files (plots, CSVs) from experiment runs in GCS. Automatically selects the latest run for each matched experiment and presents a confirmation screen before downloading.

## Options

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `-e, --exp-filter PATTERN` | Required | Glob pattern to match experiment paths (fnmatch) | - |
| `-o, --output-dir DIR` | Optional | Output directory | `./downloads` |
| `--name-format {long,short}` | Optional | Filename format | `long` |
| `--nest-runs` | Flag | Add `{run_id}/` subdirectory under each experiment | Disabled |
| `--bucket BUCKET` | Optional | GCS bucket name | From config |
| `--dir-prefix PREFIX` | Optional | GCS directory prefix | From config |
| `-y, --yes` | Flag | Skip confirmation prompt | Disabled |

### Name Formats

- **`long`** (default): Flattened GCS path as filename (e.g., `experiment-name__output__plot.png`). Avoids collisions when downloading from multiple experiments.
- **`short`**: Original basename only (e.g., `plot.png`). Shorter but may collide across experiments.

## Examples

```bash
# Download plots for all experiments in a month
epycloud download -e "202607/"

# Download for a specific experiment pattern
epycloud download -e "202607/hosp_*"

# Custom output directory
epycloud download -e "202607/" -o ./results

# Short filenames with run subdirectories
epycloud download -e "202607/" --name-format short --nest-runs

# Skip confirmation
epycloud download -e "202607/" -y

# Pipe-friendly: data output on stdout, progress on stderr
epycloud download -e "202607/" 2>/dev/null
```

## Workflow

1. **Search**: Scans GCS for experiments matching the pattern
2. **Resolve**: Finds the latest run ID for each matched experiment
3. **Plan**: Shows a download plan with file counts and run details
4. **Confirm**: Prompts for confirmation (skip with `-y`)
5. **Download**: Downloads files and reports per-experiment results

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (GCS error, download failure) |
| `2` | Configuration error |

## Related Commands

- [`epycloud experiment list`](experiment.md) - Browse experiments and runs on GCS
- [`epycloud workflow list`](workflow.md#list) - List workflow executions
