# Experiment Data

Experiment data lives in a dedicated GitHub repository (e.g., `flu-forecast-epydemix`) and provides everything Stage A needs to build simulation tasks.

## Repository Structure

```
{experiment-repo}/
├── experiments/
│   └── {EXP_ID}/
│       └── config/
│           ├── basemodel.yaml       # Model structure, parameters, populations
│           ├── modelset.yaml         # Populations, calibration or sampling settings (optional)
│           ├── output.yaml                  # Output generation settings (optional)
│           └── output_projection.yaml       # Alternative output config (optional)
├── common-data/                            # Shared data files
│   ├── surveillance/                       # Surveillance data (e.g., ILI rates)
│   └── parameters/                         # Shared parameter files
└── functions/                              # Custom Python modules
    └── custom_models.py                    # User-defined model functions
```

## Loading experiment data

Experiment data are loaded from different sources depending on the execution mode.

| Mode | Mechanism |
|------|-----------|
| **Cloud** | Builder clones the experiment repo from GitHub at runtime (PAT required if private) |
| **Local** | Experiment data is mounted from `./local/forecast/` into containers |

In cloud mode, the forecast repository is configured in the profile config:

```yaml
# profiles/flu.yaml
github:
  forecast_repo: mobs-lab/flu-forecast-epydemix  # GitHub repo to clone
  forecast_repo_ref: ""                           # Branch/tag/commit (empty = default branch)
```

In this case, Stage A clones `mobs-lab/flu-forecast-epydemix` from GitHub at the default branch into `/data/forecast/` inside the container. Experiment configs are then available at `/data/forecast/experiments/{EXP_ID}/config/`. Setting `forecast_repo_ref` to a branch, tag, or commit pins the clone to that specific version.

In local mode, experiment data must be placed in `./local/forecast/` before running. This can be done by writing configs directly or copying from an existing experiment repository. Docker Compose mounts `./local/forecast/` to `/data/forecast/` inside the container.

## Configuration Files

| File | Purpose | Required |
|------|---------|----------|
| `basemodel.yaml` | Model structure: compartments, transitions, parameters, populations | Yes |
| `modelset.yaml` | Population definitions and scenario variants. Contains calibration settings (particles, fitting windows, priors) or sampling settings (parameter distributions, strategy) depending on workflow type | No |
| `output.yaml` | Output generation settings (quantiles, trajectories, posteriors, hub formats) | No |
