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
| `--files PATTERN` | Optional | Comma-separated filenames/globs to download, replacing the defaults | Default file set |
| `--bucket BUCKET` | Optional | GCS bucket name | From config |
| `--dir-prefix PREFIX` | Optional | GCS directory prefix | From config |
| `-y, --yes` | Flag | Skip confirmation prompt | Disabled |

### Selecting Files

By default, each matched run's `outputs/` directory is searched for a fixed set of plots:

- `posterior_grid.pdf`
- `quantiles_grid_sidebyside.pdf`
- `categorical_rate_trends.pdf` (only for experiments whose name starts with `hosp_`)

Use `--files` to download a different set. It accepts comma-separated [fnmatch](https://docs.python.org/3/library/fnmatch.html) glob patterns and **replaces** the defaults entirely (the `hosp_` rule no longer applies). Patterns match against the file basename, e.g.:

- `--files quantiles_grid_sidebyside.pdf` — a single named file
- `--files "*.pdf"` — every PDF in `outputs/`
- `--files "*.pdf,*.csv.gz"` — all PDFs and compressed CSVs
- `--files "posterior_*"` — files with a given prefix

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

# Download only one specific plot
epycloud download -e "202607/" --files quantiles_grid_sidebyside.pdf

# Download all PDFs and compressed CSVs (glob patterns)
epycloud download -e "202607/hosp_*" --files "*.pdf,*.csv.gz"

# Skip confirmation
epycloud download -e "202607/" -y

# Pipe-friendly: data output on stdout, progress on stderr
epycloud download -e "202607/" 2>/dev/null
```

## Output Directory Structure

**Default** (`--name-format long`):

```bash
epycloud download -e "202607/"
```

```
downloads/
├── 202607/exp1/
│   ├── 202607_exp1_20260218-..._outputs_..._posterior_grid.pdf
│   └── 202607_exp1_20260218-..._outputs_..._quantiles_grid_sidebyside.pdf
└── 202607/hosp_exp2/
    ├── 202607_hosp_exp2_20260217-..._outputs_..._posterior_grid.pdf
    ├── 202607_hosp_exp2_20260217-..._outputs_..._quantiles_grid_sidebyside.pdf
    └── 202607_hosp_exp2_20260217-..._outputs_..._categorical_rate_trends.pdf
```

Long names flatten the GCS path (with `dir_prefix` stripped) into the filename using `_`, so each file is unique even if multiple experiments share the same output filenames.

**`--name-format short`**:

```bash
epycloud download -e "202607/" --name-format short
```

```
downloads/
└── 202607/exp1/
    ├── posterior_grid.pdf
    └── quantiles_grid_sidebyside.pdf
```

**`--name-format short --nest-runs`**:

```bash
epycloud download -e "202607/" --name-format short --nest-runs
```

```
downloads/
└── 202607/exp1/
    └── 20260218-143015-a1b2c3d4/
        ├── posterior_grid.pdf
        └── quantiles_grid_sidebyside.pdf
```

Experiments starting with `hosp_` also download `categorical_rate_trends.pdf`.

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
