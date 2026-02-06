# Configuration Variables

Complete reference for all configuration keys, their types, and default values. These keys can be set in any configuration file (base `config.yaml`, environments, profiles, or project config).

For an introduction to the configuration system, file locations, and resolution order, see [Configuring epycloud](../user-guide/configuration/index.md).

## When each config is used

Configuration keys are consumed at three different points: **infrastructure deployment**, **image building**, and **workflow execution**. Understanding this helps you know which changes require redeploying infrastructure versus just re-running a workflow.

### Infrastructure deployment

These keys are read when you run `epycloud terraform apply`. Their resolved values are **baked into the deployed Cloud Workflows definition and Cloud infrastructure**. Changing them in your config (whether in base, an environment, or a profile) has **no effect until you run `terraform apply` again**.

| Keys | Purpose |
|------|---------|
| `google_cloud.project_id`, `region`, `bucket_name` | Project infrastructure |
| `docker.repo_name`, `image_name`, `image_tag` | *Default* image URI in workflow |
| `google_cloud.batch.task_count_per_node` | *Default* tasks per VM |
| `google_cloud.batch.stage_a.*` | *Default* Stage A resources |
| `google_cloud.batch.stage_b.*` | *Default* Stage B resources |
| `google_cloud.batch.stage_c.*` (including `run_output_stage`) | *Default* Stage C resources and behavior |

!!! note
    Any key not defined in your config (across all layers) falls back to the default in Terraform's `variables.tf`, which matches the [config template defaults](#complete-template).

### Image building

These keys are read when you run `epycloud build`. They determine what goes into the Docker image. Changing them requires rebuilding.

| Keys | Purpose |
|------|---------|
| `google_cloud.project_id`, `region` | Registry path |
| `docker.*` | Image name, tag, registry |
| `github.modeling_suite_repo`, `modeling_suite_ref` | Which modeling suite version to install |
| `github.personal_access_token` | Auth for private repos (local/dev builds only) |

### Workflow execution

These keys are read each time you run `epycloud run workflow`. Changes **take effect immediately** on the next run **without redeploying** infrastructure. Some of these can also override the terraform-baked defaults.

| Keys | Purpose | Overrides terraform default? |
|------|---------|------------------------------|
| `google_cloud.project_id`, `region`, `bucket_name` | Where to submit and store data | No (must match deployed infra) |
| `storage.dir_prefix` | GCS path prefix | N/A (runtime only) |
| `docker.image_tag` | Which image tag to use for this run | Yes |
| `github.forecast_repo` | Experiment repo to clone | N/A (runtime only) |
| `github.forecast_repo_ref` | Branch/tag to checkout | N/A (runtime only) |
| `google_cloud.batch.max_parallelism` | Max parallel tasks | Yes |
| `google_cloud.batch.task_count_per_node` | Tasks per VM | Yes |
| `google_cloud.batch.stage_*/machine_type` | Machine type per stage (empty = auto-select based on CPU/memory) | Yes (via CLI flags) |
| `google_cloud.batch.stage_*/cpu_milli`, `memory_mib` | CPU/memory per stage | Yes (via CLI flags, together with machine type) |

!!! tip
    You can override machine types, parallelism, and image tag per run without redeploying infrastructure. This is useful for testing different resource allocations or running with a specific image version.

## Environment Variable Overrides

Any configuration key can be overridden using environment variables with the `EPYCLOUD_` prefix. Use double underscores (`__`) to separate nested paths. This works for every key listed on this page.

**Examples:**

| YAML path | Environment variable |
|-----------|----------------------|
| `google_cloud.project_id` | `EPYCLOUD_GOOGLE_CLOUD__PROJECT_ID` |
| `google_cloud.batch.stage_b.cpu_milli` | `EPYCLOUD_GOOGLE_CLOUD__BATCH__STAGE_B__CPU_MILLI` |
| `docker.image_tag` | `EPYCLOUD_DOCKER__IMAGE_TAG` |
| `storage.dir_prefix` | `EPYCLOUD_STORAGE__DIR_PREFIX` |

## storage

Directory prefix for organizing pipeline data in GCS (or local filesystem).

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `storage.dir_prefix` | string | `"pipeline/{environment}/{profile}"` | Base directory prefix for all pipeline data. Supports template variables `{environment}` and `{profile}`, which are interpolated at runtime. |

**Example paths after interpolation:**

- `pipeline/prod/flu/` (environment=prod, profile=flu)
- `pipeline/dev/covid/` (environment=dev, profile=covid)

## google_cloud

Google Cloud Platform project and region settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.project_id` | string | _(required)_ | Google Cloud project ID (e.g., `my-gcp-project`). |
| `google_cloud.region` | string | `us-central1` | Google Cloud region for all resources (Batch jobs, GCS, Artifact Registry). |
| `google_cloud.bucket_name` | string | _(required)_ | GCS bucket for pipeline input/output data. Must already exist. |

## google_cloud.batch

Cloud Batch job configuration controlling parallelism and per-stage compute resources.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.max_parallelism` | integer | `100` | Maximum number of Stage B tasks running simultaneously. Cloud Batch limit is 5000. |
| `google_cloud.batch.task_count_per_node` | integer | `1` | Number of tasks per VM. Set to `1` for dedicated VMs per task (recommended for predictable performance). |

### google_cloud.batch.stage_a

Compute resources for Stage A (Builder). Single-task job that generates input files for Stage B.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.stage_a.cpu_milli` | integer | `2000` | CPU allocation in millicores (2000 = 2 vCPUs). |
| `google_cloud.batch.stage_a.memory_mib` | integer | `8192` | Memory allocation in MiB (8192 = 8 GB). |
| `google_cloud.batch.stage_a.machine_type` | string | `"c4d-standard-2"` | Google Cloud machine type. Empty string (`""`) lets Cloud Batch auto-select based on CPU/memory requirements. |
| `google_cloud.batch.stage_a.max_run_duration` | integer | `3600` | Maximum execution time in seconds (3600 = 1 hour). Tasks exceeding this limit are terminated. |

### google_cloud.batch.stage_b

Compute resources for Stage B (Runner). Parallel tasks, each processing one input file.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.stage_b.cpu_milli` | integer | `2000` | CPU allocation in millicores (2000 = 2 vCPUs). |
| `google_cloud.batch.stage_b.memory_mib` | integer | `8192` | Memory allocation in MiB (8192 = 8 GB). |
| `google_cloud.batch.stage_b.machine_type` | string | `""` | Google Cloud machine type. Empty string lets Cloud Batch auto-select. Set explicitly (e.g., `"e2-standard-2"`) for predictable scaling. |
| `google_cloud.batch.stage_b.max_run_duration` | integer | `36000` | Maximum execution time in seconds (36000 = 10 hours). See [sizing guidelines](#sizing-guidelines) below. |

### google_cloud.batch.stage_c

Compute resources for Stage C (Output). Runs as a single task that loads all Stage B results into memory, so it typically needs more memory than the other stages.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.stage_c.cpu_milli` | integer | `4000` | CPU allocation in millicores (4000 = 4 vCPUs). |
| `google_cloud.batch.stage_c.memory_mib` | integer | `15360` | Memory allocation in MiB (15360 = 15 GB). |
| `google_cloud.batch.stage_c.machine_type` | string | `"c4d-standard-4"` | Google Cloud machine type. Empty string lets Cloud Batch auto-select. |
| `google_cloud.batch.stage_c.max_run_duration` | integer | `7200` | Maximum execution time in seconds (7200 = 2 hours). See [sizing guidelines](#sizing-guidelines) below. |
| `google_cloud.batch.stage_c.run_output_stage` | boolean | `true` | Whether to run Stage C after Stage B completes. Set to `false` to skip output generation (e.g., when only raw runner artifacts are needed). |

### Sizing guidelines

**Stage B (Runner):**

| Workload | Recommended `max_run_duration` |
|----------|-------------------------------|
| Short simulations (< 1 hour) | `3600` |
| Medium simulations (1-5 hours) | `18000` |
| Long simulations (5-10 hours) | `36000` (default) |
| Very long simulations | Up to `604800` (7 days, Cloud Batch limit) |

**Stage C (Output):**

| Workload | Recommended `max_run_duration` | Memory guidance |
|----------|-------------------------------|-----------------|
| Small runs (< 100 tasks) | `1800` (30 min) | 8 GB sufficient |
| Medium runs (100-1,000 tasks) | `7200` (default) | 8-15 GB |
| Large runs (1,000-10,000 tasks) | `14400` (4 hours) | 16-32 GB |

### Machine type selection

When `machine_type` is set to a specific value (e.g., `"c4d-standard-2"`):

- Cloud Batch provisions that exact machine type
- `cpu_milli` and `memory_mib` act as task-level constraints (must fit within the machine)

When `machine_type` is empty (`""`):

- Cloud Batch auto-selects a VM based on `cpu_milli` and `memory_mib`
- Recommended when you don't need a specific machine family

For available machine types, pricing, and sizing recommendations, see [Machine Types](google-cloud/machine-types.md).

## docker

Docker image configuration for the pipeline container.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `docker.registry` | string | `"us-central1-docker.pkg.dev"` | Container registry URL. For Artifact Registry, format is `{region}-docker.pkg.dev`. |
| `docker.repo_name` | string | `"epymodelingsuite-repo"` | Artifact Registry repository name. |
| `docker.image_name` | string | `"epymodelingsuite"` | Docker image name. |
| `docker.image_tag` | string | `"latest"` | Docker image tag. Use specific tags (e.g., `v1.0.0`) in production. |

The full image URI is constructed as:

```
{registry}/{google_cloud.project_id}/{repo_name}/{image_name}:{image_tag}
```

## github

GitHub repository references for the modeling suite package and experiment data.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `github.modeling_suite_repo` | string | `"mobs-lab/epymodelingsuite"` | GitHub repository for the modeling suite package (format: `owner/repo`). Cloned during Docker build. |
| `github.modeling_suite_ref` | string | `"main"` | Branch, tag, or commit to use when building the Docker image. |
| `github.forecast_repo` | string | _(profile-specific)_ | GitHub repository for experiment data (format: `owner/repo`). Typically set in profile configs. Cloned at runtime by Stage A and Stage C. |
| `github.forecast_repo_ref` | string | `""` | Branch, tag, or commit to checkout after cloning the forecast repo. Empty string uses the repository's default branch. |
| `github.personal_access_token` | string | _(secrets.yaml)_ | GitHub PAT for accessing private repositories. Store in `secrets.yaml`, not in `config.yaml`. See [Secrets](../user-guide/configuration/secrets.md). |

## logging

Logging configuration for pipeline scripts and the CLI.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `logging.level` | string | `"INFO"` | Log level. One of: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `logging.storage_verbose` | boolean | `true` | Enable verbose logging for storage operations (uploads, downloads, listings). |

## workflow

Cloud Workflows orchestration settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `workflow.retry_policy.max_attempts` | integer | `3` | Maximum retry attempts for failed workflow steps. |
| `workflow.retry_policy.backoff_seconds` | integer | `60` | Backoff duration in seconds between retries. |
| `workflow.notification.enabled` | boolean | `false` | Enable workflow completion/failure notifications. |
| `workflow.notification.email` | string | `null` | Email address for workflow notifications. Requires `notification.enabled: true`. |

!!! note "Runtime Environment Variables"
    For pipeline runtime variables (`NUM_TASKS`, `ALLOW_PARTIAL_RESULTS`, `BATCH_TASK_INDEX`, etc.) that are not part of the configuration file system, see [Environment Variables](environment-variables.md).

## Complete Template

For reference, here is the full default `config.yaml` template:

```yaml title="config.yaml"
# Storage configuration
storage:
  dir_prefix: "pipeline/{environment}/{profile}"

# Google Cloud Platform configuration
google_cloud:
  project_id: your-gcp-project-id
  region: us-central1
  bucket_name: your-bucket-name

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

# Docker image configuration
docker:
  registry: "us-central1-docker.pkg.dev"
  repo_name: epymodelingsuite-repo
  image_name: epymodelingsuite
  image_tag: latest

# GitHub repositories
github:
  modeling_suite_repo: mobs-lab/epymodelingsuite
  modeling_suite_ref: main
  forecast_repo_ref: ""

# Logging configuration
logging:
  level: INFO
  storage_verbose: true

# Workflow configuration
workflow:
  retry_policy:
    max_attempts: 3
    backoff_seconds: 60
  notification:
    enabled: false
    email: null
```
