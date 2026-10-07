# Configuration Variables

Complete reference for all configuration keys, their types, and default values. These keys can be set in any configuration file (base `config.yaml`, environments, profiles, or project config).

For an introduction to the configuration system, file locations, and resolution order, see [Configuring epycloud](../user-guide/configuration/index.md).

## When each config is used

Configuration keys are consumed at three different points: **infrastructure deployment**, **image building**, and **workflow execution**. Understanding this helps you know which changes require redeploying infrastructure versus just re-running a workflow.

### Infrastructure deployment

These keys are read when you run `epycloud terraform apply`. Their resolved values are **baked into the deployed Cloud Workflows definition and Cloud infrastructure**. Changing them in your config (whether in base, an environment, or a profile) has **no effect until you run `terraform apply` again**.

| Keys | Purpose |
|------|---------|
| `google_cloud.project_id`, `region`, `batch_regions`, `bucket_name` | Control-plane and regional data-plane infrastructure |
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
| `execution.provider` | Cloud execution backend (`gcp` is currently supported) | N/A |
| `storage.dir_prefix` | GCS path prefix | N/A (runtime only) |
| `docker.image_tag` | Which image tag to use for this run | Yes |
| `github.forecast_repo` | Experiment repo to clone | N/A (runtime only) |
| `github.forecast_repo_ref` | Branch/tag to checkout | N/A (runtime only) |
| `google_cloud.billing_project` | Cost grouping label for billing reports | N/A (runtime only) |
| `google_cloud.batch.max_parallelism` | Max parallel tasks | Yes |
| `google_cloud.batch.task_count_per_node` | Tasks per VM | Yes |
| `google_cloud.batch.stage_*/machine_types` | Ordered fallback candidates per stage | Yes |
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

## execution

Selects the backend used for cloud pipeline and stage execution. Configurations
created before this setting was introduced continue to use GCP.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `execution.provider` | string | `gcp` | Cloud execution backend. Only `gcp` is currently supported. |

## google_cloud

Google Cloud Platform project and region settings.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.project_id` | string | _(required)_ | Google Cloud project ID (e.g., `my-gcp-project`). |
| `google_cloud.region` | string | `us-central1` | Control-plane region for Cloud Workflows and the default Batch region. |
| `google_cloud.batch_regions` | mapping | `us-central1`, `us-east5` | Allowed Batch regions mapped to distinct subnet CIDRs. Terraform creates one subnet, router, NAT, and Artifact Registry repository per entry. |
| `google_cloud.bucket_name` | string | _(required)_ | GCS bucket for pipeline input/output data. Must already exist. |
| `google_cloud.billing_project` | string | `""` | User-defined label for cost grouping in GCP billing reports. Applied to all Cloud Batch jobs. Can be overridden per run with `--billing-project`. |

Each data-plane region needs a non-overlapping subnet range:

```yaml
google_cloud:
  region: us-central1
  batch_regions:
    us-central1:
      subnet_cidr: 10.0.0.0/20
    us-east5:
      subnet_cidr: 10.1.0.0/20
```

## google_cloud.batch

Cloud Batch job configuration controlling parallelism and per-stage compute resources.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.max_parallelism` | integer | `100` | Maximum number of Stage B tasks running simultaneously. Cloud Batch limit is 5000. |
| `google_cloud.batch.task_count_per_node` | integer | unset | Optional cap on Stage B tasks per VM. When unset, each machine candidate runs as many tasks as fit its vCPUs and memory (minus a 1024 MiB reserve when tasks share a VM). Set to `1` for dedicated VMs per task. |

### google_cloud.batch.stage_a

Compute resources for Stage A (Builder). Single-task job that generates input files for Stage B.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.stage_a.cpu_milli` | integer | `2000` | CPU allocation in millicores (2000 = 2 vCPUs). |
| `google_cloud.batch.stage_a.memory_mib` | integer | `7168` | Minimum memory allocation in MiB. |
| `google_cloud.batch.stage_a.machine_types` | list | C4D, C4, N4D, N4 standard-2 | Ordered fallback candidates. Every candidate must meet the stage minimums. |
| `google_cloud.batch.stage_a.max_run_duration` | integer | `3600` | Maximum execution time in seconds (3600 = 1 hour). Tasks exceeding this limit are terminated. |

### google_cloud.batch.stage_b

Compute resources for Stage B (Runner). Parallel tasks, each processing one input file.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.stage_b.cpu_milli` | integer | `2000` | CPU requested by each task, in millicores (1000 = 1 vCPU). Also decides how many tasks fit on each machine candidate. |
| `google_cloud.batch.stage_b.memory_mib` | integer | `7168` | Memory requested by each task, in MiB. Also decides how many tasks fit on each machine candidate. |
| `google_cloud.batch.stage_b.machine_types` | list | C4D, C4, N4D, N4 standard-2 | Ordered fallback candidates. |
| `google_cloud.batch.stage_b.max_run_duration` | integer | `36000` | Maximum execution time in seconds (36000 = 10 hours). See [sizing guidelines](#sizing-guidelines) below. |

### google_cloud.batch.stage_c

Compute resources for Stage C (Output). Runs as a single task that loads all Stage B results into memory, so it typically needs more memory than the other stages.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `google_cloud.batch.stage_c.cpu_milli` | integer | `4000` | CPU allocation in millicores (4000 = 4 vCPUs). |
| `google_cloud.batch.stage_c.memory_mib` | integer | `15360` | Memory allocation in MiB (15360 = 15 GB). |
| `google_cloud.batch.stage_c.machine_types` | list | C4D, C4, N4D, C3 standard-4 | Ordered fallback candidates. A memory-bound profile can replace this list with highmem-4 candidates. |
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

### CPU per task and tasks per VM

`cpu_milli` and `memory_mib` are what **one task** requests. For each machine candidate, epycloud computes how many Stage B tasks fit on one VM:

```
tasks per VM = min(machine vCPUs / cpu_milli, (machine memory - 1024 MiB) / memory_mib)
```

The 1024 MiB is left for the OS and container runtime when tasks share a VM (one task may use the whole VM). The workflow caps the result at the number of Stage B tasks, and `task_count_per_node` (or `--task-count-per-node`) caps it further when set.

**Even packing.** Batch provisions `floor(tasks / tasks per VM)` VMs, so a remainder waits until a slot frees up (51 tasks at 4 per VM get 12 VMs and 3 waiting tasks). Once Stage A has produced the tasks, the workflow lowers each candidate to the largest divisor of the Stage B parallelism that keeps at least 3/4 of its VM busy (51 tasks run at 3 per VM on 17 VMs). It then tries the candidates that pack evenly first, keeping `machine_types` order within each group. A one-task-per-VM candidate always packs evenly, so including a small machine such as `c4d-highcpu-2` in the chain removes the wait for any task count.

**Request one physical core per single-threaded task.** On Compute Engine a vCPU is one hardware thread, and two vCPUs share each physical core. Stage B calibration runs in one thread, so `cpu_milli: 1000` puts two tasks on each physical core. Measured on `c3d-standard-4` with the flu model:

| `cpu_milli` | Tasks per `c3d-standard-4` | Time per task | Cost per task |
|-------------|----------------------------|---------------|---------------|
| `1000` | 4 (two per physical core) | ~1.9x longer | about the same |
| `2000` | 2 (one per physical core) | baseline | about the same |

Sharing a core halves the price per task-hour but nearly doubles the run time, so it saves nothing and makes runs about twice as long. Keep `cpu_milli: 2000` (one physical core) unless the task is I/O-bound or multithreaded.

Packing only pays off when a run has at least as many tasks as fit on one VM. For one or two tasks, a 2-vCPU machine (one physical core) costs less than a mostly idle 4-vCPU VM; order `machine_types` accordingly.

### Machine type selection

When `machine_types` contains multiple values:

- The workflow tries candidates in order
- Every candidate gets the same per-task request; a smaller machine only fits fewer tasks
- An unsuccessful candidate is cancelled and drained before replacement

When a `--stage-*-machine-type` CLI option is supplied:

- The stage is pinned to that one candidate
- The per-task `cpu_milli` and `memory_mib` still come from the config, and the machine must fit at least one task

The legacy singular `machine_type` key remains a one-candidate compatibility path. Run `epycloud config migrate` to replace legacy keys with requirement-based chains.

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

# Cloud execution backend
execution:
  provider: gcp

# Google Cloud Platform configuration
google_cloud:
  project_id: your-gcp-project-id
  region: us-central1
  bucket_name: your-bucket-name
  billing_project: ""

  batch:
    max_parallelism: 100
    task_count_per_node: 1

    stage_a:
      cpu_milli: 2000
      memory_mib: 7168
      machine_types: [c4d-standard-2, c3-highcpu-4, n4d-standard-2, n4-standard-2]
      max_run_duration: 3600

    stage_b:
      cpu_milli: 2000
      memory_mib: 7168
      machine_types: [c4d-standard-2, c3-highcpu-4, n4d-standard-2, n4-standard-2]
      max_run_duration: 36000

    stage_c:
      cpu_milli: 4000
      memory_mib: 15360
      machine_types: [c4d-standard-4, c3-standard-4, n4d-standard-4, n4-standard-4]
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
