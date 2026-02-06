# Base Configuration

The base configuration file (`config.yaml`) contains shared defaults that apply to all environments and profiles. It is the foundation of the [configuration hierarchy](index.md): every other layer (environments, profiles, secrets) overrides values defined here, and anything not overridden is inherited from base.

This is where you set values that rarely change between environments, such as your Google Cloud project, region, and bucket.

## Creating the base config

```console
$ epycloud config init       # Creates config.yaml with defaults
$ epycloud config edit       # Open in $EDITOR
```

## What belongs in base config

These are the typical items that are configured in the base config:

- **Google Cloud project and region** (usually the same everywhere)
- **Docker registry and repository** (shared image infrastructure)
- **Modeling suite repository** (same package for all projects)
- **Default resource allocations** (can be overridden per environment)
- **Logging defaults**

Settings that vary or needs override should go in [environments](environments.md) (infrastructure differences) or [profiles](profiles.md) (project-specific values) instead.

!!! note "Default fallbacks"
    Any key not defined in your config falls back to Terraform defaults (which match the config template defaults). See [When each config is used](../../reference/configuration-variables.md#when-each-config-is-used) for details on which keys are read at infrastructure deployment, image building, and workflow execution.

## Example

```yaml title="~/.config/epymodelingsuite-cloud/config.yaml"
storage:
  dir_prefix: "pipeline/{environment}/{profile}"

google_cloud:
  project_id: "my-gcp-project"
  region: "us-central1"
  bucket_name: "my-modeling-bucket"

  batch:
    max_parallelism: 100
    task_count_per_node: 1

    stage_a:
      cpu_milli: 2000
      memory_mib: 8192
      machine_type: "c4d-standard-2"
      max_run_duration: 3600

    stage_b:
      cpu_milli: 2000
      memory_mib: 8192
      machine_type: ""
      max_run_duration: 36000

    stage_c:
      cpu_milli: 4000
      memory_mib: 15360
      machine_type: "c4d-standard-4"
      max_run_duration: 7200
      run_output_stage: true

docker:
  registry: "us-central1-docker.pkg.dev"
  repo_name: "epymodelingsuite-repo"
  image_name: "epymodelingsuite"
  image_tag: "latest"

github:
  modeling_suite_repo: "mobs-lab/epymodelingsuite"
  modeling_suite_ref: "main"
  forecast_repo_ref: ""

logging:
  level: INFO
  storage_verbose: true

workflow:
  retry_policy:
    max_attempts: 3
    backoff_seconds: 60
  notification:
    enabled: false
    email: null
```

For a description of every key, its type, and default value, see the [Configuration Variables Reference](../../reference/configuration-variables.md).

## Validating

Always validate before running workflows:

```console
$ epycloud config validate              # Validate current config
$ epycloud --env=prod config validate   # Validate with a specific environment
$ epycloud config show                  # Show fully resolved config
$ epycloud config get google_cloud.project_id  # Get a specific value
```
