# Variable Configuration

Complete reference for all configuration variables used across the project.

## Overview

All project-specific values are configurable via:
- **`.env`** - Primary configuration for Makefile and runtime (gitignored)
- **`.env.local`** - Local secrets for Docker builds (gitignored, optional)
- **Secret Manager** - Sensitive values for cloud deployment (GitHub PAT)


## Environment Variables (.env)

The `.env` file contains project-specific values used by Makefile and scripts.

**Template:** [.env.example](.env.example)

### Google Cloud Infrastructure

```bash
PROJECT_ID=your-project-id         # GCP project ID
REGION=us-central1                 # GCP region for resources
REPO_NAME=epydemix                 # Artifact Registry repository name
BUCKET_NAME=your-bucket-name       # GCS bucket (must exist)
```

### Docker Image

```bash
IMAGE_NAME=epymodelingsuite        # Docker image name
IMAGE_TAG=latest                   # Docker image tag
```

### GitHub Private Repositories

```bash
GITHUB_FORECAST_REPO=username/forecasting-repo              # Forecast data repo
GITHUB_MODELING_SUITE_REPO=username/modeling-suite-repo     # Modeling suite package
GITHUB_MODELING_SUITE_REF=main                              # Branch/commit to build
```

### Workflow Parameters

```bash
DIR_PREFIX=pipeline/flu/           # Base directory prefix in GCS
EXP_ID=default-sim                 # Default experiment ID (override at runtime)
MAX_PARALLELISM=100                # Max parallel tasks (default: 100, max: 5000)
TASK_COUNT_PER_NODE=1              # Tasks per VM (1 = dedicated VMs)
```

### Batch Compute Resources - Stage A (Dispatcher)

```bash
STAGE_A_CPU_MILLI=2000             # CPU in milli-cores (2000 = 2 vCPUs)
STAGE_A_MEMORY_MIB=4096            # Memory in MiB (4096 = 4 GB)
STAGE_A_MACHINE_TYPE=""            # VM type (empty = auto-select)
```

### Batch Compute Resources - Stage B (Runner)

```bash
STAGE_B_CPU_MILLI=2000             # CPU in milli-cores (2000 = 2 vCPUs)
STAGE_B_MEMORY_MIB=4096            # Memory in MiB (4096 = 4 GB)
STAGE_B_MACHINE_TYPE=""            # VM type (e.g., "e2-standard-2", empty = auto-select)
```

**Recommended production configuration:**
```bash
STAGE_B_MACHINE_TYPE="e2-standard-2"  # Explicit type for predictable scaling
TASK_COUNT_PER_NODE=1                 # One task per VM (no queueing)
```


## Output Structure

Workflow outputs are organized in GCS as:

```
gs://{BUCKET_NAME}/{DIR_PREFIX}{EXP_ID}/{RUN_ID}/
  inputs/input_0000.pkl, input_0001.pkl, ...
  results/result_0000.pkl, result_0001.pkl, ...
```

**Path components:**
- `BUCKET_NAME` - GCS bucket (from `.env`)
- `DIR_PREFIX` - Organizational prefix (from `.env`, optional trailing slash)
- `EXP_ID` - Experiment identifier (user provides when running workflow)
- `RUN_ID` - Auto-generated timestamp-uuid (unique per workflow execution)


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

### Local Development (.env.local)

For local Docker builds (`make build-local` and `make build-dev`), use `.env.local`.

**Template:** [.env.local.example](.env.local.example)

**Setup:**
```bash
# Copy template
cp .env.local.example .env.local

# Edit .env.local and add your PAT
# File contents:
GITHUB_PAT=your_github_pat_here

# Load variables before building
source .env.local
```

**Usage:**
```bash
# Build local development image
source .env.local
make build-dev

# Build cloud image locally and push
source .env.local
make build-local
```

**Security notes:**
- `.env.local` is gitignored - never commit it
- Only needed for local Docker builds with private repositories
- Cloud builds use Secret Manager instead
- PAT is passed to Docker as a build argument (not persisted in image layers)


## Configuration Flow

**Setup (one-time):**
1. Copy `.env.example` → `.env` and configure values
2. For local builds: Copy `.env.local.example` → `.env.local` and add GitHub PAT
3. For cloud deployment: Create GitHub PAT and store in Secret Manager
4. Run `make tf-init && make tf-apply` to deploy infrastructure

**Cloud build and deploy:**
1. Makefile reads `.env` variables
2. Passes variables to Cloud Build, Terraform, and Workflow execution
3. Terraform injects variables into workflow YAML via `templatefile()`
4. Cloud Build fetches GitHub PAT from Secret Manager
5. Workflow generates unique `run_id` and constructs GCS paths

**Local build:**
1. Load both `.env` and `.env.local`: `source .env && source .env.local`
2. Makefile passes `GITHUB_PAT` from `.env.local` to Docker build
3. Docker build uses PAT to clone private repositories during image build

**Runtime:**
1. Batch jobs receive environment variables from workflow
2. Jobs fetch GitHub PAT from Secret Manager to clone repositories
3. Results stored in GCS at `{bucket}/{dirPrefix}{exp_id}/{run_id}/`

