# Variable Configuration

This document explains how configuration values are managed across the project to avoid hardcoding.

## Environment Variables (.env)

The `.env` file (gitignored) contains project-specific values used by Makefile and scripts:

```bash
# Google Cloud Infrastructure
PROJECT_ID=your-project-id
REGION=us-central1
REPO_NAME=epydemix
BUCKET_NAME=your-bucket-name

# Docker Image
IMAGE_NAME=epymodelingsuite
IMAGE_TAG=latest

# GitHub Private Repositories
GITHUB_FORECAST_REPO=username/forecasting-repo
GITHUB_MODELING_SUITE_REPO=username/modeling-suite-repo
GITHUB_MODELING_SUITE_REF=main

# Workflow Parameters
RUN_COUNT=10
RUN_SEED=1234
DIR_PREFIX=pipeline/flu/
SIM_ID=default-sim
MAX_PARALLELISM=100
```

**Usage:**
```bash
source .env
make build
make run-workflow
```

### Output Structure

Workflow outputs are organized as:
```
gs://{BUCKET_NAME}/{DIR_PREFIX}/{SIM_ID}/{RUN_ID}/inputs/input_*.pkl
gs://{BUCKET_NAME}/{DIR_PREFIX}/{SIM_ID}/{RUN_ID}/results/result_*.pkl
```

Where:
- `DIR_PREFIX` - Organizational prefix (configurable, optional trailing slash)
- `SIM_ID` - User-provided simulation identifier (passed to workflow)
- `RUN_ID` - Auto-generated from workflow execution ID (unique per run)

## Terraform Variables

### Input Variables (terraform/variables.tf)
- `project_id` - Google Cloud Project ID
- `region` - Google Cloud region (default: "us-central1")
- `repo_name` - Artifact Registry repository name (default: "epydemix")
- `bucket_name` - GCS bucket name
- `image_name` - Docker image name (default: "epymodelingsuite")
- `image_tag` - Docker image tag (default: "latest")
- `github_forecast_repo` - Private GitHub repo for forecasting (format: "username/reponame")

### Configuration (terraform/terraform.tfvars)
User-specific values (gitignored):
```hcl
project_id            = "your-gcp-project-id"
region                = "us-central1"
repo_name             = "epymodelingsuite-repo"
bucket_name           = "your-bucket-name"
image_name            = "epymodelingsuite"
image_tag             = "latest"
github_forecast_repo  = "owner/forecasting-repo"
```

### Template (terraform/terraform.tfvars.example)
Example template (committed to git) for new users.

## Workflow YAML (terraform/workflow.yaml)

Uses Terraform `templatefile()` to inject variables:
- `${repo_name}` - Artifact Registry repo name
- `${image_name}` - Docker image name
- `${image_tag}` - Docker image tag
- `$${...}` - Escaped for Workflows runtime variables

## Cloud Build (cloudbuild.yaml)

Uses substitution variables with defaults:
- `${_REGION}` - Region (default: "us-central1")
- `${_REPO_NAME}` - Repo name (default: "epymodelingsuite-repo")
- `${_IMAGE_NAME}` - Image name (default: "epymodelingsuite")
- `${_IMAGE_TAG}` - Image tag (default: "latest")

Override via Makefile:
```bash
make build  # Uses env vars
```

Or manually:
```bash
gcloud builds submit --substitutions=_REGION=us-west1,_REPO_NAME=myrepo
```

## Manual Job Templates (jobs/)

Template files use environment variables:
- `stage-a.json.template` - Stage A template
- `stage-b.json.template` - Stage B template

Generate concrete files:
```bash
source .env
./jobs/generate-jobs.sh
```

**Configurable parameters in generate-jobs.sh:**
- `TASK_COUNT` - Number of tasks (default: 10)
- `PARALLELISM` - Maximum parallel tasks (default: 100)
- `COUNT`, `SEED` - Stage A parameters
- `IN_PREFIX`, `OUT_PREFIX`, `RESULTS_PREFIX` - GCS paths

Generated files (gitignored):
- `jobs/stage-a.json`
- `jobs/stage-b.json`

## Workflow Runtime Variables

The workflow receives these parameters at runtime:

```json
{
  "count": 10,
  "seed": 1234,
  "bucket": "bucket-name",
  "dirPrefix": "pipeline/flu/",
  "sim_id": "winter-2024",
  "batchSaEmail": "batch-runtime@project.iam.gserviceaccount.com",
  "githubForecastRepo": "owner/forecasting-repo",
  "maxParallelism": 100
}
```

**Parameter descriptions:**
- `count` - Number of input files to generate in Stage A
- `seed` - Random seed for reproducibility
- `bucket` - GCS bucket name for inputs/outputs
- `dirPrefix` - Organizational prefix (optional, adds trailing slash if missing)
- `sim_id` - User-provided simulation identifier
- `batchSaEmail` - Service account email for Batch jobs
- `githubForecastRepo` - Private GitHub repository for forecasting (format: "owner/repo")
- `maxParallelism` - **Optional** - Maximum parallel tasks in Stage B (default: 100, max: 5000 per Cloud Batch limits)

The workflow then:
1. Extracts `run_id` from the workflow execution ID (auto-generated)
2. Normalizes `dirPrefix` (adds trailing slash if needed)
3. Constructs paths: `{dirPrefix}{sim_id}/{run_id}/inputs/` and `/results/`
4. Sets `parallelism = min(N, maxParallelism)` for Stage B
5. Passes environment variables to container tasks:
   - `EXECUTION_MODE` - "cloud" (enables cloud storage and GitHub cloning)
   - `SIM_ID`, `RUN_ID` - Simulation and run identifiers
   - `GITHUB_FORECAST_REPO` - Forecast repository to clone
   - `FORECAST_REPO_DIR` - Directory to clone forecast repo to (default: `/data/forecast/`)
   - `GITHUB_PAT_SECRET` - Secret Manager secret name for GitHub PAT
   - `GCLOUD_PROJECT_ID` - Project ID for accessing secrets

## GitHub Authentication

### Secret Manager Setup

The project uses Google Secret Manager to securely store the GitHub Personal Access Token (PAT):

**Secret name:** `github-pat` (referenced in terraform/main.tf)

**Create the secret:**
```bash
echo -n "your_github_pat_here" | gcloud secrets create github-pat \
  --data-file=- \
  --project=${PROJECT_ID}
```

**Update the secret:**
```bash
echo -n "new_pat_value" | gcloud secrets versions add github-pat \
  --data-file=- \
  --project=${PROJECT_ID}
```

### GitHub PAT Requirements

The PAT must be a **fine-grained personal access token** with:
- **Repository access**: Select specific repositories (epymodelingsuite, forecasting)
- **Permissions**: Contents (read-only)
- **Expiration**: Set appropriate expiration and rotate regularly

### Runtime Usage

During Batch job execution:
1. `run_dispatcher.sh` fetches PAT from Secret Manager using `gcloud secrets versions access`
2. Uses PAT to clone private repository via HTTPS: `https://oauth2:TOKEN@github.com/owner/repo.git`
3. PAT is only in memory, never written to disk
4. Service account (`batch-runtime`) has `roles/secretmanager.secretAccessor` permission

## Configuration Flow

1. **User sets values** in `.env` (for scripts/Make) and `terraform/terraform.tfvars` (for Terraform)
2. **User creates GitHub PAT** and stores in Secret Manager as `github-pat`
3. **Makefile** reads `.env` and passes to:
   - Cloud Build (via `--substitutions`)
   - Terraform (via `-var` flags)
   - Workflow execution (via `--data` JSON with `dirPrefix`, `sim_id`, and `githubForecastRepo`)
4. **Terraform** uses `terraform.tfvars` and `templatefile()` to:
   - Deploy infrastructure
   - Create Secret Manager secret resource (shell only, value added manually)
   - Grant service account access to secret
   - Generate workflow YAML with correct image URI
5. **Workflow** extracts `run_id` from execution ID and constructs full paths
6. **Batch jobs** fetch PAT from Secret Manager at runtime to clone private repos
7. **Job generator** reads `.env` to create manual test templates

## No Hardcoded Values

All project-specific values (project IDs, regions, bucket names, image names) are now configurable via:
- `.env` for Makefile/scripts
- `terraform.tfvars` for Terraform
- Template files for manual jobs

This allows the codebase to be portable across different Google Cloud projects and environments.
