# Variable Configuration

Complete reference for all configuration variables used across the project.

## Overview

All project-specific values are configurable via the unified configuration system:
- **`config.yaml`** - Primary configuration (`~/.config/epymodelingsuite-cloud/config.yaml`)
- **`secrets.yaml`** - Secrets like GitHub PAT (`~/.config/epymodelingsuite-cloud/secrets.yaml`, 0600 permissions)
- **Environment configs** - Environment-specific overrides (`~/.config/epymodelingsuite-cloud/environments/{env}.yaml`)
- **Secret Manager** - Cloud deployment secrets (GitHub PAT)

**Configuration commands:**
```bash
epycloud config init          # Initialize configuration
epycloud config edit          # Edit base configuration
epycloud config edit-secrets  # Edit secrets
epycloud config show          # Show merged configuration
```

## Configuration Structure (config.yaml)

The configuration file uses YAML format with hierarchical structure:

```yaml
# Google Cloud Infrastructure
google_cloud:
  project_id: your-project-id         # GCP project ID
  region: us-central1                 # GCP region for resources
  bucket_name: your-bucket-name       # GCS bucket (must exist)

  # Cloud Batch Configuration
  batch:
    max_parallelism: 100              # Max parallel tasks (default: 100, max: 5000)
    task_count_per_node: 1            # Tasks per VM (1 = dedicated VMs)

    # Stage A (Builder) Resources
    stage_a:
      cpu_milli: 2000                 # CPU (2000 = 2 vCPUs)
      memory_mib: 4096                # Memory (4096 = 4 GB)
      machine_type: ""                # VM type (empty = auto-select)
      max_run_duration: 3600          # Timeout in seconds (1 hour)

    # Stage B (Runner) Resources
    stage_b:
      cpu_milli: 2000                 # CPU (2000 = 2 vCPUs)
      memory_mib: 4096                # Memory (4096 = 4 GB)
      machine_type: ""                # VM type (e.g., "e2-standard-2", empty = auto-select)
      max_run_duration: 36000         # Timeout in seconds (10 hours)

    # Stage C (Output) Resources
    stage_c:
      cpu_milli: 2000                 # CPU (2000 = 2 vCPUs)
      memory_mib: 8192                # Memory (8192 = 8 GB)
      machine_type: ""                # VM type (empty = auto-select)
      max_run_duration: 7200          # Timeout in seconds (2 hours)

    run_output_stage: true            # Enable/disable Stage C

# Docker Configuration
docker:
  registry: us-central1-docker.pkg.dev
  repo_name: epymodelingsuite-repo    # Artifact Registry repository name
  image_name: epymodelingsuite        # Docker image name
  image_tag: latest                   # Docker image tag

# GitHub Repositories
github:
  forecast_repo: username/forecasting-repo        # Forecast data repo
  modeling_suite_repo: username/modeling-suite    # Modeling suite package
  modeling_suite_ref: main                        # Branch/commit to build

# Storage
storage:
  dir_prefix: "pipeline/{environment}/{profile}"  # Base directory prefix in GCS

# Logging
logging:
  level: INFO                         # Log level (DEBUG, INFO, WARNING, ERROR)
  storage_verbose: true               # Enable verbose storage operations
```

### Timeout Configuration

**Stage B (Runner):**
- `max_run_duration`: Maximum time allowed for each Stage B task to complete
- Default: 36000 seconds (10 hours)
- Tasks exceeding this limit will be terminated by Google Cloud Batch
- Adjust based on your simulation runtime requirements:
  - Short simulations (< 1 hour): 3600 seconds
  - Medium simulations (1-5 hours): 18000 seconds
  - Long simulations (5-10 hours): 36000 seconds (default)
  - Very long simulations: Up to 604800s (7 days, Cloud Batch limit)

**Stage C (Output):**
- Stage C aggregates all Stage B results into formatted CSV outputs
- Single task job (not parallelized)
- Memory requirements increase with number of Stage B tasks
- Default: 8 GB (suitable for up to ~1000 tasks)
- Increase memory for larger runs (10,000+ tasks may need 16-32 GB)
- Timeout guidelines:
  - Small runs (< 100 tasks): 1800 seconds (30 minutes)
  - Medium runs (100-1000 tasks): 7200 seconds (2 hours, default)
  - Large runs (1000-10,000 tasks): 14400 seconds (4 hours)
  - Very large runs (10,000+ tasks): Increase as needed

### Recommended Production Configuration

```yaml
google_cloud:
  batch:
    task_count_per_node: 1            # One task per VM (no queueing)
    stage_b:
      machine_type: "e2-standard-2"   # Explicit type for predictable scaling
      cpu_milli: 2000
      memory_mib: 8192
```


## Output Structure

Workflow outputs are organized in GCS as:

```
gs://{BUCKET_NAME}/{DIR_PREFIX}{EXP_ID}/{RUN_ID}/
  builder-artifacts/
    input_0000.pkl, input_0001.pkl, ...
  runner-artifacts/
    result_0000.pkl, result_0001.pkl, ...
  outputs/
    quantiles_compartments.csv.gz
    quantiles_transitions.csv.gz
    trajectories_compartments.csv.gz
    trajectories_transitions.csv.gz
    model_metadata.csv.gz
    posteriors.csv.gz  (calibration only)
```

**Path components:**
- `BUCKET_NAME` - GCS bucket (from `google_cloud.bucket_name`)
- `DIR_PREFIX` - Organizational prefix (from `storage.dir_prefix`)
- `EXP_ID` - Experiment identifier (user provides when running workflow)
- `RUN_ID` - Auto-generated timestamp-uuid (unique per workflow execution)

**Output directories:**
- `builder-artifacts/` - Stage A input files (N pickle files)
- `runner-artifacts/` - Stage B result files (N pickle files)
- `outputs/` - Stage C formatted CSV files (only created if `run_output_stage: true`)


## GitHub Authentication

GitHub Personal Access Token (PAT) is required to access private repositories.

**PAT requirements:**
- Type: Fine-grained personal access token
- Repository access: Select specific repositories (modeling suite, forecast)
- Permissions: Contents (read-only)
- Expiration: Set and rotate regularly

See [google-cloud-guide.md](google-cloud-guide.md#setting-up-github-personal-access-token) for detailed PAT creation instructions.

### Cloud Deployment (Secret Manager)

For cloud builds and workflow execution, store PAT in Google Secret Manager.

**Secret name:** `github-pat`

**Setup:**
```bash
# Get project ID from config
PROJECT_ID=$(epycloud config show | grep 'project_id:' | awk '{print $2}')

# Create secret (first time)
echo -n "your_github_pat" | gcloud secrets create github-pat \
  --data-file=- \
  --project=${PROJECT_ID}

# Update secret (when rotating)
echo -n "new_github_pat" | gcloud secrets versions add github-pat \
  --data-file=- \
  --project=${PROJECT_ID}
```

**Usage:**
- Cloud Build fetches PAT to install modeling suite package
- Batch jobs fetch PAT to clone forecast repository
- Service accounts have `secretmanager.secretAccessor` role

### Local Development (secrets.yaml)

For local Docker builds, configure GitHub PAT in `secrets.yaml`.

**Location:** `~/.config/epymodelingsuite-cloud/secrets.yaml`

**Setup:**
```bash
# Edit secrets file (creates with 0600 permissions)
epycloud config edit-secrets

# Add your GitHub PAT:
github:
  personal_access_token: github_pat_xxxxxxxxxxxxx

# Verify it's configured
epycloud config show | grep personal_access_token
```

**Usage:**
```bash
# Build local development image (PAT loaded automatically)
epycloud build dev

# Build cloud image locally and push
epycloud build local
```

**Security notes:**
- `secrets.yaml` is automatically created with 0600 permissions (user read/write only)
- Located in `~/.config/epymodelingsuite-cloud/` (not in project directory)
- Only needed for local Docker builds with private repositories
- Cloud builds use Secret Manager instead
- PAT is passed to Docker as a build argument (not persisted in image layers)


## Configuration Flow

**Setup (one-time):**
1. Initialize configuration: `epycloud config init`
2. Edit base config: `epycloud config edit`
3. Edit secrets: `epycloud config edit-secrets` (add GitHub PAT)
4. For cloud deployment: Create GitHub PAT and store in Secret Manager
5. Deploy infrastructure: `epycloud terraform init && epycloud terraform apply`

**Configuration hierarchy (lowest to highest priority):**
1. Base config (`config.yaml`)
2. Environment config (`environments/{env}.yaml`)
3. Profile config (`profiles/{profile}.yaml`)
4. Project config (`./epycloud.yaml`, optional)
5. Secrets (`secrets.yaml`, merged into config)
6. Template interpolation (variables like `{environment}`, `{profile}`)
7. Environment variables (`EPYCLOUD_*` prefix overrides)

**Cloud build and deploy:**
1. `epycloud` CLI loads merged configuration from config files
2. Passes configuration to Cloud Build, Terraform, and Workflow execution
3. Terraform injects variables into workflow YAML via `templatefile()`
4. Cloud Build fetches GitHub PAT from Secret Manager
5. Workflow generates unique `run_id` and constructs GCS paths

**Local build:**
1. `epycloud build dev` loads configuration automatically
2. Reads GitHub PAT from `secrets.yaml`
3. Passes configuration and PAT to Docker build
4. Docker build uses PAT to clone private repositories during image build

**Runtime:**
1. Batch jobs receive environment variables from workflow
2. Jobs fetch GitHub PAT from Secret Manager to clone repositories
3. Results stored in GCS at `{bucket}/{dirPrefix}{exp_id}/{run_id}/`

## Environment Variable Overrides

You can override any configuration value using environment variables with the `EPYCLOUD_` prefix:

```bash
# Override project ID
export EPYCLOUD_GOOGLE_CLOUD__PROJECT_ID=my-other-project

# Override image tag
export EPYCLOUD_DOCKER__IMAGE_TAG=v1.2.3

# Override GitHub repository
export EPYCLOUD_GITHUB__MODELING_SUITE_REF=feature-branch

# Run command with overrides
epycloud build cloud
```

**Path separator:** Use double underscore `__` to separate nested paths (e.g., `GOOGLE_CLOUD__PROJECT_ID` → `google_cloud.project_id`)

## Runtime Environment Variables

These environment variables are used by the pipeline scripts during job execution and are not part of the configuration system.

### Stage A/C (Builder/Output) Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `FORECAST_REPO_REF` | Branch/tag/commit to checkout after cloning the forecast repo | (default branch) | `202547`, `test` |

**FORECAST_REPO_REF Usage:**

When `FORECAST_REPO_REF` is set, the builder and output scripts will checkout the specified ref after cloning the forecast repository:

```bash
# Via CLI
epycloud run workflow --exp-id my-exp --forecast-repo-ref test-202546

# Via config file (github.forecast_repo_ref)
```

### Stage C (Output) Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NUM_TASKS` | Number of Stage B result files to load | 1 | `52` |
| `ALLOW_PARTIAL_RESULTS` | Allow generating outputs with partial results when some tasks fail | `true` | `false`, `0`, `no` |

**ALLOW_PARTIAL_RESULTS Usage:**

By default (`true`), Stage C continues with partial results if some Stage B tasks are missing or failed. This allows output generation even when a small number of tasks fail.

Setting `ALLOW_PARTIAL_RESULTS=false` enables strict mode where Stage C fails if any tasks are missing:

```bash
# Local execution with strict mode (fail if any tasks missing)
ALLOW_PARTIAL_RESULTS=false epycloud run job --local --stage output --exp-id my-exp --run-id <run_id> --num-tasks 52

# Cloud execution (set in terraform/workflow.yaml or batch job environment)
```

**When to use partial results (default):**
- A small percentage of tasks failed (e.g., 2 out of 52 tasks)
- The failed tasks are not critical to your analysis
- You want to examine partial results while debugging task failures

**When to use strict mode (ALLOW_PARTIAL_RESULTS=false):**
- You need complete coverage for publication/production
- Failed tasks represent critical scenarios or parameters
- Many tasks failed (indicates systemic issue requiring investigation)

**Output behavior with partial results:**
- Stage C logs warnings about missing/failed tasks
- Generates outputs using only successfully completed tasks
- Telemetry summary shows completion rate (e.g., "50/52 tasks")
- Users should verify data coverage is adequate for their needs

## Migration from .env Files

If you have existing `.env` files, migrate to the unified config system:

**Mapping: .env → config.yaml**

| Old .env Variable | New config.yaml Path |
|------------------|----------------------|
| `PROJECT_ID` | `google_cloud.project_id` |
| `REGION` | `google_cloud.region` |
| `BUCKET_NAME` | `google_cloud.bucket_name` |
| `REPO_NAME` | `docker.repo_name` |
| `IMAGE_NAME` | `docker.image_name` |
| `IMAGE_TAG` | `docker.image_tag` |
| `GITHUB_FORECAST_REPO` | `github.forecast_repo` |
| `FORECAST_REPO_REF` | `github.forecast_repo_ref` |
| `GITHUB_MODELING_SUITE_REPO` | `github.modeling_suite_repo` |
| `GITHUB_MODELING_SUITE_REF` | `github.modeling_suite_ref` |
| `DIR_PREFIX` | `storage.dir_prefix` |
| `MAX_PARALLELISM` | `google_cloud.batch.max_parallelism` |
| `TASK_COUNT_PER_NODE` | `google_cloud.batch.task_count_per_node` |
| `STAGE_A_CPU_MILLI` | `google_cloud.batch.stage_a.cpu_milli` |
| `STAGE_A_MEMORY_MIB` | `google_cloud.batch.stage_a.memory_mib` |
| `STAGE_A_MACHINE_TYPE` | `google_cloud.batch.stage_a.machine_type` |
| `STAGE_B_CPU_MILLI` | `google_cloud.batch.stage_b.cpu_milli` |
| `STAGE_B_MEMORY_MIB` | `google_cloud.batch.stage_b.memory_mib` |
| `STAGE_B_MACHINE_TYPE` | `google_cloud.batch.stage_b.machine_type` |
| `STAGE_B_MAX_RUN_DURATION` | `google_cloud.batch.stage_b.max_run_duration` |
| `STAGE_C_CPU_MILLI` | `google_cloud.batch.stage_c.cpu_milli` |
| `STAGE_C_MEMORY_MIB` | `google_cloud.batch.stage_c.memory_mib` |
| `STAGE_C_MACHINE_TYPE` | `google_cloud.batch.stage_c.machine_type` |
| `STAGE_C_MAX_RUN_DURATION` | `google_cloud.batch.stage_c.max_run_duration` |
| `RUN_OUTPUT_STAGE` | `google_cloud.batch.run_output_stage` |
| `LOG_LEVEL` | `logging.level` |
| `STORAGE_VERBOSE` | `logging.storage_verbose` |

**Mapping: .env.local → secrets.yaml**

| Old .env.local Variable | New secrets.yaml Path |
|------------------------|----------------------|
| `GITHUB_PAT` | `github.personal_access_token` |

