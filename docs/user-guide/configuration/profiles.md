# Profiles

Profiles are **configuration layers** for organizing settings by project. In the [configuration hierarchy](index.md), profiles sit above [environments](environments.md), so profile values take precedence over the resolved base + environment config. They are commonly used to maintain separate configurations for different modeling projects (Flu, COVID, RSV), but they can represent any logical grouping of project-level overrides.

For example, each disease project might use a different experiment repository and storage prefix. Profiles let you switch between these with a single command.

## Using profiles

You activate a profile once with `epycloud profile use <name>`, and it **stays active** across all subsequent commands until you switch to a different one.

```console
$ epycloud profile use flu              # Activate flu profile (persists)
$ epycloud profile current              # Show active profile
$ epycloud profile list                 # List available profiles
$ epycloud profile create mpox          # Create new profile
```

## What belongs in a profile

Profile files only need to contain keys you want to override from the resolved [environment](environments.md) and [base config](base.md). Everything else is inherited. Typical settings include:

- Experiment repository (`github.forecast_repo`)
- Experiment repository branch (`github.forecast_repo_ref`)
- Storage prefix (`storage.dir_prefix`)
- Project-specific resource requirements

For infrastructure differences (image tags, modeling suite branches, resource scaling), consider using [environments](environments.md) instead.

## Examples

A flu profile pointing to the flu experiment repository:

```yaml title="profiles/flu.yaml"
github:
  forecast_repo: "your-org/flu-forecast-experiments"

storage:
  dir_prefix: "pipeline/flu/"

google_cloud:
  batch:
    stage_b:
      cpu_milli: 2000
      memory_mib: 8192
```

A covid profile with a different repository and higher resources:

```yaml title="profiles/covid.yaml"
github:
  forecast_repo: "your-org/covid-forecast-experiments"

# Use different path in Google Cloud Storage
storage:
  dir_prefix: "pipeline/covid/"

# For example if you are running heavier calibration, you can use more computing resource
google_cloud:
  batch:
    stage_b:
      cpu_milli: 4000
      memory_mib: 16384
```

## Usage

```console
# Activate flu profile
$ epycloud profile use flu
$ epycloud run workflow --exp-id weekly-forecast-1  # Uses flu settings

# Activate COVID profile
$ epycloud profile use covid
$ epycloud run workflow --exp-id covid-model-1      # Uses covid settings
```

Profiles and environments combine naturally:

```console
$ epycloud profile use flu
$ epycloud --env dev run workflow --exp-id test     # flu + dev
$ epycloud --env prod run workflow --exp-id prod    # flu + prod
```

## Managing profiles

```console
$ epycloud profile list                 # List available profiles
$ epycloud profile create mpox          # Create new profile from template
$ epycloud config edit --profile=mpox   # Edit profile config
$ epycloud profile use mpox             # Switch to new profile
```

For all available configuration keys, see the [Configuration Variables Reference](../../reference/configuration-variables.md).
