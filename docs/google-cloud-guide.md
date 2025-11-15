# Google Cloud Guide

This document provides complete setup and implementation details for the Google Cloud pipeline (Cloud Batch + Workflows) using Terraform, Docker images, and lightweight scripts.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Design and Architecture](#design-and-architecture)
- [1) Repository Structure](#1-repository-structure)
- [2) Prerequisites](#2-prerequisites)
  - [IAM Permissions](#iam-permissions)
  - [Setting up GitHub Personal Access Token](#setting-up-github-personal-access-token)
- [3) Terraform](#3-terraform)
- [4) Workflow YAML](#4-workflow-yaml)
- [5) Compute Resources and Instance Types](#5-compute-resources-and-instance-types)
  - [Understanding cpuMilli, memoryMib, and Machine Types](#understanding-cpumilli-memorymib-and-machine-types)
  - [Current Resource Allocation](#current-resource-allocation)
  - [Tuning Compute Resources](#tuning-compute-resources)
  - [Recommended Configuration: Dedicated VMs (taskCountPerNode=1)](#recommended-configuration-dedicated-vms-taskcountpernode1)
- [6) Docker Image](#6-docker-image)
  - [Multi-stage Build Architecture](#multi-stage-build-architecture)
  - [Build & Push](#build--push)
  - [Local Execution with Docker Compose](#local-execution-with-docker-compose)
    - [Running Locally](#running-locally)
    - [Docker Compose Configuration](#docker-compose-configuration)
- [7) Scripts](#7-scripts)
  - [Stage A Wrapper: scripts/run_builder.sh](#stage-a-wrapper-scriptsrun_dispatchersh)
  - [Stage A: scripts/main_builder.py](#stage-a-scriptsmain_dispatcherpy)
  - [Stage B: scripts/main_runner.py](#stage-b-scriptsmain_runnerpy)
- [8) Monitoring and Resource Groups](#8-monitoring-and-resource-groups)
  - [Label Structure](#label-structure)
  - [Monitoring Dashboards](#monitoring-dashboards)
  - [Custom Filtering](#custom-filtering)
- [9) epycloud CLI](#9-epycloud-cli)
- [10) Operational Notes](#10-operational-notes)
- [11) Billing and Cost Tracking](#11-billing-and-cost-tracking)
- [12) Implementation Summary](#12-implementation-summary)

## Quick Reference

Here are the essential commands to setup the pipeline. Please read the full documentation before actual execution.

```bash
# 1. Set up environment variables
cp .env.example .env

# Edit .env with your project details (PROJECT_ID, REGION, BUCKET_NAME, etc.)
source .env

# 2. Create GitHub PAT and store in Secret Manager
echo -n "your_github_pat_here" | gcloud secrets create github-pat \
  --data-file=- \
  --project=${PROJECT_ID}

# 3. Initialize and deploy infrastructure
epycloud terraform init
epycloud terraform plan    # Review changes first
epycloud terraform apply

# 4. Build and push Docker image
epycloud build cloud

# 5. Add experiment file to your forecast repository and git push

# 6. Run your first workflow
epycloud run workflow --exp-id initial-test

# 7. Monitor execution
epycloud status
epycloud workflow list --exp-id initial-test

# 8. View logs and details
epycloud workflow describe <execution-id>
epycloud logs --exp-id initial-test
```

**Next steps:**
- Continue reading for detailed explanations of each component
- See [operations.md](operations.md) for daily operational commands
- See [variable-configuration.md](variable-configuration.md) for configuration reference

## Design and architecture

The pipeline is consisted from following tech stacks/components:

* **Infrastructure-as-code (Terraform)** for:
  * Artifact Registry (container repo)
  * GCS buckets/prefixes (builder-artifacts/runner-artifacts, optional logs)
  * Service Accounts & IAM (Workflows runner, Batch runtime)
  * Workflows (deployed from YAML)
* **Container image** (Dockerfile + requirements) with both Stage A / Stage B entrypoints
* **Scripts**:
  * `run_builder.sh` (Setups and runs stage A).
  * `main_builder.py` (Stage A: produce N pickled inputs)
  * `main_runner.py` (Stage B: consume one pickle per task using `BATCH_TASK_INDEX`)
* **Workflow YAML**:
  * Orchestrates: Stage A → wait → list GCS → Stage B (`taskCount=N`) → wait
* **Makefile (optional)**: common commands (build/push/deploy/run)


## 1) Repository structure

```
epymodelingsuite-cloud/
├─ terraform/
│  ├─ main.tf                    # Google Cloud resources
│  ├─ variables.tf
│  ├─ outputs.tf
│  ├─ workflow.yaml              # Workflows orchestration definition
│  └─ terraform.tfvars           # Project-specific values
├─ docker/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ scripts/                   # Docker runtime scripts
│     ├─ main_builder.py         # Stage A: Generate N input files
│     ├─ main_runner.py          # Stage B: Process individual tasks
│     ├─ main_output.py          # Stage C: Aggregate results
│     ├─ run_builder.sh          # Stage A wrapper for repo cloning
│     └─ run_output.sh           # Stage C wrapper
├─ Makefile                      # Build/deploy automation
├─ cloudbuild.yaml               # Cloud Build configuration
├─ .env                          # Environment variables (gitignored)
├─ .env.example                  # Template for environment variables
├─ .gitignore
└─ README.md
```


## 2) Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated to target project: `gcloud auth login`, `gcloud config set project <PROJECT_ID>`
- [Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli) ≥ 1.5
- [Docker](https://docs.docker.com/engine/install/)
  - For Mac, [OrbStack](https://orbstack.dev/) is recommended over Docker Desktop for lightweight and faster experience.
- Python 3.11 (for local dev)
- Make
- **GitHub Fine-Grained Personal Access Token (PAT)** - required for accessing private repositories (epymodelingsuite and forecasting)

### IAM Permissions

To deploy and run this infrastructure, you need the following IAM permissions in addition to the Editor role (`roles/editor`):

**Required roles:**
- **Project IAM Admin** (`roles/resourcemanager.projectIamAdmin`) - To manage project-level IAM bindings (Terraform)
- **Secret Manager Admin** (`roles/secretmanager.admin`) - To manage IAM policies for secrets (Terraform)
- **Service Account Admin** (`roles/iam.serviceAccountAdmin`) - To manage IAM policies on service accounts (Terraform)
- **Cloud Build Editor** (`roles/cloudbuild.builds.editor`) - To submit and manage Cloud Build jobs (Docker builds)

**Grant permissions to your user account:**
```bash
# Project IAM Admin (required for Terraform to create project-level role bindings)
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="user:user@example.com" \
  --role="roles/resourcemanager.projectIamAdmin"

# Secret Manager Admin (required for Terraform to set IAM policies on secrets)
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="user:user@example.com" \
  --role="roles/secretmanager.admin"

# Service Account Admin (required for Terraform to set IAM policies on service accounts)
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="user:user@example.com" \
  --role="roles/iam.serviceAccountAdmin"

# Cloud Build Editor (required to build and push Docker images)
gcloud projects add-iam-policy-binding your-gcp-project-id \
  --member="user:user@example.com" \
  --role="roles/cloudbuild.builds.editor"
```

**Common permission errors:**
- `Error 403: Policy update access denied` → Need Project IAM Admin and Secret Manager Admin roles
- `Permission 'iam.serviceAccounts.setIamPolicy' denied` → Need Service Account Admin role
- `The caller does not have permission` (Cloud Build) → Need Cloud Build Editor role

**Note**: Ask your Google Cloud project administrator to grant these roles if you encounter permission errors during deployment.

Set these environment variables:

```bash
# Copy the template and fill in your values
cp .env.example .env

# Edit .env with your project details
# The examples are:
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
export REPO_NAME=epymodelingsuite-repo
export BUCKET_NAME=your-bucket-name  # Assumes existing bucket

# GitHub Private Repositories
export GITHUB_FORECAST_REPO=owner/forecasting-repo  # Forecast data (format: owner/repo)
export GITHUB_MODELING_SUITE_REPO=owner/epymodelingsuite  # Modeling suite package (format: owner/repo)
export GITHUB_MODELING_SUITE_REF=main  # Branch or commit to build from

# After editing, load the variables
source .env
```


**Note**: The terraform does not make a new bucket, but rather uses an **existing GCS bucket**.

### Setting up GitHub Personal Access Token

The pipeline requires a GitHub Fine-Grained Personal Access Token (PAT) to clone private repositories during Docker build and Batch job execution.

**Create a fine-grained PAT:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set appropriate name and expiration
4. Under "Repository access", select "Only select repositories" and add:
   - `epymodelingsuite` repository
   - Your forecast repository
5. Under "Repository permissions", grant:
   - **Contents**: Read-only access
6. Generate and copy the token

**Store the PAT in Google Secret Manager:**
```bash
# Store the PAT (replace with your actual token). For the first time, run:
 echo -n "github_pat_xxxxxxxxxxxxx" | gcloud secrets create github-pat \
  --data-file=- \
  --project=${PROJECT_ID}

# Update PAT (second time or later)
  echo -n "github_pat_xxxx" | gcloud secrets versions add github-pat \
  --data-file=- \
  --project=${PROJECT_ID}

# Verify it was created
gcloud secrets describe github-pat --project=${PROJECT_ID}
```

**Important notes:**
- The secret name must be `github-pat` to match the Terraform configuration
- Never commit the PAT to version control
- Set an appropriate expiration date and rotate regularly
- Single PAT provides access to multiple repositories with granular permissions


## 3) Terraform

We use Terraform to manage core cloud resources and workflow. See full implementation in [terraform/main.tf](terraform/main.tf), [terraform/variables.tf](terraform/variables.tf), and [terraform/outputs.tf](terraform/outputs.tf).

**Key resources:**
- **APIs**: Enables `batch.googleapis.com`, `workflows.googleapis.com`, `artifactregistry.googleapis.com`, `secretmanager.googleapis.com`
- **Artifact Registry**: Docker repository for container images
- **GCS Bucket**: Uses existing bucket via `data "google_storage_bucket"`
- **Secret Manager**: Stores GitHub PAT (`github-pat`) for repository access
- **Service Accounts**:
  - `batch_runtime_sa`: For running Batch jobs
  - `workflows_runner_sa`: For executing workflows
- **IAM**:
  - Batch SA has `roles/storage.objectAdmin` on bucket
  - Batch SA has `roles/secretmanager.secretAccessor` for GitHub PAT
  - Workflows SA has `roles/batch.jobsAdmin` and `roles/iam.serviceAccountUser`
- **Workflows**: Deploys from [terraform/workflow.yaml](terraform/workflow.yaml)

**Important notes:**
- Uses existing GCS bucket (not creating new one)
- Uses `batch.jobsAdmin` role (more restrictive than `batch.admin`)
- Includes logging permissions for Batch jobs
- GitHub PAT secret must be created manually before applying Terraform


## 4) Workflow YAML

See full implementation in [terraform/workflow.yaml](terraform/workflow.yaml).

**Orchestration flow:**
1. **Stage A (Generator)**: Single Batch job that runs `main_builder.py` to generate N input files
2. **List inputs**: Counts generated files in GCS
3. **Stage B (Runner)**: Parallel Batch jobs (N tasks) running `main_runner.py`, each processing one input
4. **Stage C (Output)**: Single Batch job that runs `main_output.py` to aggregate results and generate CSV outputs
5. **Wait helper**: Polls Batch job status until completion

**Key features:**
- Takes runtime parameters: `count`, `seed`, `bucket`, `dirPrefix`, `exp_id`, `batchSaEmail`, `githubForecastRepo`, `maxParallelism` (optional, default: 100)
- Auto-generates `run_id` from workflow execution ID for unique identification
- Constructs paths: `{dirPrefix}{exp_id}/{run_id}/builder-artifacts/`, `/runner-artifacts/`, and `/outputs/`
- Stage A: 2 CPU, 4 GB RAM, includes repo cloning via [run_builder.sh](scripts/run_builder.sh)
- Stage B: 2 CPU, 8 GB RAM, configurable parallelism (default: 100, max: 5000 per Cloud Batch limits)
- Stage C: 2 CPU, 8 GB RAM, aggregates all Stage B results and generates formatted CSV outputs
- GitHub authentication via PAT from Secret Manager
- Logs to Cloud Logging
- Error handling for failed/deleted jobs
- Returns job names and task count

## 5) Compute Resources and Instance Types

### Understanding cpuMilli, memoryMib, and Machine Types

Google Cloud Batch allows you to specify compute resources in two ways:

**Option 1: Automatic VM selection (recommended for getting started)**
- Set `cpuMilli` and `memoryMib` to define task requirements
- Leave `STAGE_B_MACHINE_TYPE=""` (empty)
- Google Cloud **automatically selects** an appropriate VM type
- Example: `cpuMilli=2000, memoryMib=4096` → Google may provision `c4d-standard-2` (2 vCPU, 7 GB)

**Option 2: Explicit machine type (recommended for production)**
- Set `STAGE_B_MACHINE_TYPE="c4d-standard-2"`
- `cpuMilli` and `memoryMib` become **task constraints** (must fit within the VM)
- Ensures predictable VM provisioning and scaling behavior
- Better for avoiding task queueing with `TASK_COUNT_PER_NODE=1`

**cpuMilli** represents thousandths of a vCPU:
- `1000 cpuMilli = 1 vCPU`
- `2000 cpuMilli = 2 vCPUs`
- `4000 cpuMilli = 4 vCPUs`

**Important relationship:**
```
If STAGE_B_MACHINE_TYPE is set:
  - cpuMilli/memoryMib = task requirements (must fit in VM)
  - Machine type determines actual VM resources
  - Example: e2-standard-2 (2 vCPU, 8 GB) with cpuMilli=2000 → 1 task per VM

If STAGE_B_MACHINE_TYPE is empty:
  - cpuMilli/memoryMib = basis for automatic VM selection
  - Google chooses VM type that fits requirements
  - Less predictable scaling behavior
```

See [Google Cloud Batch documentation](https://cloud.google.com/batch/docs/create-run-job#resources) for details.

### Current Resource Allocation

**Cloud Build** - [cloudbuild.yaml:38](../cloudbuild.yaml#L38)
```yaml
machineType: E2_HIGHCPU_8
```
- [Predefined instance type](https://cloud.google.com/build/pricing?hl=en) for build operations. Note that the only options for CloudBuild are `e2-medium`, `e2-standard-2`, `e2-highcpu-8`, and `e2-highcpu-32`. See documentation for details.
- `e2-highcpu-8`: 8 vCPU, 8 GB RAM (provides faster builds with more CPU)

**Stage A Job (Generator)**
```yaml
computeResource:
  cpuMilli: ${STAGE_A_CPU_MILLI}    # Default: 2000 (2 vCPUs)
  memoryMib: ${STAGE_A_MEMORY_MIB}  # Default: 4096 (4 GB RAM)
```
- Single task that generates input files
- Configurable via `.env`: `STAGE_A_CPU_MILLI`, `STAGE_A_MEMORY_MIB`, `STAGE_A_MACHINE_TYPE`
- Default resources: 2 vCPUs, 4 GB RAM

**Stage B Job (Runner)**
```yaml
computeResource:
  cpuMilli: ${STAGE_B_CPU_MILLI}    # Default: 2000 (2 vCPUs)
  memoryMib: ${STAGE_B_MEMORY_MIB}  # Default: 4096 (4 GB RAM)
maxRunDuration: ${STAGE_B_MAX_RUN_DURATION}s  # Default: 36000s (10 hours)
taskCountPerNode: ${TASK_COUNT_PER_NODE}  # Default: 1 (dedicated VM per task)
```
- Parallel tasks processing individual simulations
- Configurable via `.env`: `STAGE_B_CPU_MILLI`, `STAGE_B_MEMORY_MIB`, `STAGE_B_MACHINE_TYPE`, `STAGE_B_MAX_RUN_DURATION`, `TASK_COUNT_PER_NODE`
- Default resources: 2 vCPUs, 4 GB RAM per task
- Default timeout: 36000 seconds (10 hours) per task

**Stage C Job (Output)**
```yaml
computeResource:
  cpuMilli: ${STAGE_C_CPU_MILLI}    # Default: 2000 (2 vCPUs)
  memoryMib: ${STAGE_C_MEMORY_MIB}  # Default: 8192 (8 GB RAM)
maxRunDuration: ${STAGE_C_MAX_RUN_DURATION}s  # Default: 7200s (2 hours)
```
- Single task that aggregates all Stage B results
- Configurable via `.env`: `STAGE_C_CPU_MILLI`, `STAGE_C_MEMORY_MIB`, `STAGE_C_MACHINE_TYPE`, `STAGE_C_MAX_RUN_DURATION`
- Default resources: 2 vCPUs, 8 GB RAM
- Default timeout: 7200 seconds (2 hours)

### Tuning Compute Resources

Resources are now **configurable via environment variables** in `.env`:

**Example configurations:**

```bash
# Lightweight tasks (1 vCPU, 2 GB)
export STAGE_B_CPU_MILLI=1000
export STAGE_B_MEMORY_MIB=2048
export STAGE_B_MACHINE_TYPE=""  # Auto-select

# Standard tasks (2 vCPUs, 8 GB) - Default
export STAGE_B_CPU_MILLI=2000
export STAGE_B_MEMORY_MIB=8192
export STAGE_B_MACHINE_TYPE="e2-standard-2"

# Compute-intensive tasks (2 vCPUs, 7 GB)
export STAGE_B_CPU_MILLI=2000
export STAGE_B_MEMORY_MIB=7168
export STAGE_B_MACHINE_TYPE="c4d-standard-2"

# High-memory tasks (2 vCPUs, 15 GB)
export STAGE_B_CPU_MILLI=8000
export STAGE_B_MEMORY_MIB=15360
export STAGE_B_MACHINE_TYPE="c4d-highmem-2"
```

**Timeout configurations:**

```bash
# Short simulations (< 1 hour)
export STAGE_B_MAX_RUN_DURATION=3600  # 1 hour

# Medium simulations (1-5 hours)
export STAGE_B_MAX_RUN_DURATION=18000  # 5 hours

# Long simulations (5-10 hours) - Default
export STAGE_B_MAX_RUN_DURATION=36000  # 10 hours

# Very long simulations (customize as needed)
export STAGE_B_MAX_RUN_DURATION=86400  # 24 hours
# Note: Cloud Batch max limit is 604800s (7 days)
```

**Important notes:**
- Tasks exceeding `STAGE_B_MAX_RUN_DURATION` will be terminated by Google Cloud Batch
- Set this value based on your longest expected simulation runtime
- Add buffer time (e.g., if max simulation is 8 hours, set to 10 hours)
- Monitor task completion times to optimize this setting

### Recommended Configuration: Dedicated VMs (taskCountPerNode=1)

For parallel execution with no task queueing, use **one task per VM**:

```bash
# Recommended configuration in .env
export TASK_COUNT_PER_NODE=1
export STAGE_B_CPU_MILLI=2000
export STAGE_B_MEMORY_MIB=8192
export STAGE_B_MACHINE_TYPE="c4d-standard-2"  # Explicit type for predictable scaling
```

**Benefits:**
- **No queueing**: Each task gets its own VM immediately
- **Efficient resource usage**: VMs terminate when tasks finish
- **Cost-effective for variable runtimes**: Pay only for actual task duration
- **Predictable scaling**: With explicit machine type, Batch provisions expected number of VMs

**How it works:**
```
With TASK_COUNT_PER_NODE=1:
  - Google Cloud Batch creates up to N VMs for N tasks
  - Each VM runs exactly 1 task then terminates
  - If machine type is set, VM creation is predictable
  - If machine type is empty, Batch may create fewer VMs (hitting quota/availability limits)
```

**Production recommendations:**
1. **Set explicit `STAGE_B_MACHINE_TYPE`** for predictable VM provisioning
2. **Match `STAGE_B_CPU_MILLI` to machine capacity**: e.g. `c4d-standard-2` (2 vCPU) → `CPU_MILLI=2000`
3. **Set `TASK_COUNT_PER_NODE=1`** for parallel execution with variable task runtimes
4. **Monitor first run** in Cloud Console to verify expected number of VMs are created


**Machine type options:**

`c4d-standard-2` provides the optimal balance of performance and cost for our workloads. A typical calibration task in Stage B for a single state uses approximately 4GB of memory, making the 7GB available in `c4d-standard-2` sufficient with headroom. Since epymodelingsuite computations are **single-threaded**, tasks only require 1 vCPU (`CPU_MILLI=1000`). However, setting `CPU_MILLI=1000` without an explicit machine type causes Google Cloud to auto-select slower `e2-standard` instances. We use dedicated small VMs with `TASK_COUNT_PER_NODE=1` and `c4d-standard-2` because it provides predictable scaling and leverages faster AMD EPYC Genoa processors for optimal single-thread performance.

While larger shared VMs could maximize vCPU utilization and reduce per-task costs, they introduce unpredictable queueing when simulation runtimes vary significantly. (Some tasks finish quickly while others run longer, extending billing duration until the slowest task on each VM completes.) Using a dedicated VM with 2 vCPUs, the average vCPU utilization will be around 50%, but this ensures consistent performance and faster overall job completion, making it the preferred choice despite slightly higher vCPU costs.

| Machine Type | vCPU | Memory (GB) | CPU_MILLI | MEMORY_MIB | Price (us-central1)* | Notes |
|--------------|------|-------------|-----------|------------|---------------------|-------|
| `e2-standard-2` | 2 | 8 | 2000 | 8192 | $0.06701142/hr | Most cost-effective, general purpose. |
| `n2-standard-2` | 2 | 8 | 2000 | 8192 | $0.097118/hr | Better CPU performance than E2. Intel Cascade Lake/Ice Lake. |
| `c4-standard-2` | 2 | 8 | 2000 | 8192 | $0.096866/hr | Intel compute-optimized. Intel Sapphire Rapids.  |
| `c4d-standard-2` | 2 | 7 | 2000 | 7168 | $0.089876046/hr | AMD compute-optimized. AMD EPYC Genoa.  |
| `c4d-highmem-2` | 2 | 15 | 2000 | 15360 | $0.11784067/hr | High memory + compute. AMD EPYC Genoa. |

<!-- | `e2-standard-4` | 4 | 16 | 4000 | 16384 | $0.13402284/hr | Cost-effective | -->
<!-- | `n2-standard-4` | 4 | 16 | 4000 | 16384 | $0.194236/hr | Balanced performance | -->
<!-- | `c3-standard-4` | 4 | 16 | 4000 | 16384 | $0.201608/hr | Latest gen, high performance | -->
<!-- | `c4-standard-4` | 4 | 16 | 4000 | 16384 | $0.19767/hr | Intel compute-optimized | -->
<!-- | `c4d-standard-4` | 4 | 15 | 4000 | 15360 | 	$0.18324767/hr | AMD compute-optimized | -->
<!-- | `c4d-highmem-4` | 4 | 31 | 4000 | 31744 | $0.239176918/hr | High memory + compute | -->

*Prices are as of Oct 23, 2025. See [Google Cloud VM pricing](https://cloud.google.com/compute/vm-instance-pricing) for current rates, and the [doc](https://cloud.google.com/compute/docs/general-purpose-machines) for the details of machine types.

**After modifying resources:**
```bash
source .env
make tf-plan    # Review changes
make tf-apply   # Deploy updated configuration
```


## 6) Docker image

For production (cloud) and development/testing (local), all of the computation runs on a Docker container. See [docker/Dockerfile](docker/Dockerfile) and [docker/requirements.txt](docker/requirements.txt).

### Multi-stage build architecture

The Dockerfile uses multi-stage builds with three stages:

**Build stages:**

1. **base** - Common dependencies shared by both local and cloud images
   - Base image: `python:3.11-slim`
   - Installs `uv` for fast dependency management
   - Installs `google-cloud-storage` and other Python dependencies
   - **Clones and installs epymodelingsuite package** from private GitHub repository (if configured)
   - Copies scripts from [scripts/](scripts/) directory

2. **local** - Minimal image for local development
   - Builds from `base` stage
   - Size: ~300-400 MB
   - Includes Python deps, git, scripts, and epymodelingsuite
   - No gcloud CLI (uses local filesystem instead of GCS)
   - Used by Docker Compose for local testing

3. **cloud** - Production image for Google Cloud
   - Builds from `base` stage
   - Size: ~500-700 MB
   - Adds gcloud CLI for Secret Manager access
   - Default entrypoint: `main_builder.py` (Stage A)
   - Used by Cloud Batch jobs

**Image naming:**
- Image name: `epymodelingsuite` (configurable via `IMAGE_NAME` in `.env`)
- Image tag: `latest` (configurable via `IMAGE_TAG`)
- Full path: `${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/epymodelingsuite:latest`

### Build & push

```bash
# Option 1: Cloud Build (recommended for production)
epycloud build cloud

# Option 2: Build cloud image locally and push to Artifact Registry
source .env && gcloud auth configure-docker ${REGION}-docker.pkg.dev --project=${PROJECT_ID}
source .env.local  # For GITHUB_PAT
epycloud build local

# Option 3: Build local dev image (for Docker Compose, no push)
source .env.local  # For GITHUB_PAT
epycloud build dev
```

**Build targets:**
- `epycloud build cloud` - Uses Cloud Build on GCP, builds `cloud` target, pushes to Artifact Registry
- `epycloud build local` - Builds `cloud` target locally, pushes to Artifact Registry (requires auth)
- `epycloud build dev` - Builds `local` target locally, tags as `epymodelingsuite:local`, no push

**Local secrets management:**
- Create [.env.local](.env.local) (gitignored) for sensitive values like `GITHUB_PAT`
- Template available at [.env.local.example](.env.local.example)
- Required for `build-local` and `build-dev` with private repositories
- Cloud builds use Secret Manager instead

**Cloud Build configuration** in [cloudbuild.yaml](cloudbuild.yaml):
- Uses `E2_HIGHCPU_8` machine type for faster builds
- Enables layer caching with `--cache-from` and `BUILDKIT_INLINE_CACHE`
- Logs to Cloud Logging only
- Automatically pushes to Artifact Registry
- **Fetches GitHub PAT from Secret Manager** for private repository access
- Passes `GITHUB_MODELING_SUITE_REPO` and `GITHUB_MODELING_SUITE_REF` as build arguments
- Submits builds asynchronously via Makefile for non-blocking operation

**How epymodelingsuite is installed:**

The epymodelingsuite package is installed during the Docker build in the `base` stage. The [Dockerfile](docker/Dockerfile) clones the private repository using GitHub PAT and installs it via `uv`:

- Installs at **build time** (baked into the Docker image, not at runtime)
- Uses GitHub PAT from Secret Manager (Cloud Build) or `.env.local` (local builds)
- Supports specific branch/commit via `GITHUB_MODELING_SUITE_REF` build argument
- Repository is cloned to `/tmp/epymodelingsuite`, installed, then removed to keep image clean
- PAT is not persisted in image layers (security best practice)

This approach ensures all containers have the same version of epymodelingsuite and eliminates runtime dependencies on GitHub.

### Local execution with Docker Compose

#### Running locally

For local execution, first build the local image, then use the `epycloud` CLI commands:

```bash
# Build local development image
source .env.local  # For GITHUB_PAT if using private repos
epycloud build dev

# Run builder (Stage A) - this auto-generates RUN_ID
epycloud run job --local --stage builder --exp-id test-sim
# Note the RUN_ID from the output, e.g., "20251114-123045-a1b2c3"

# Run a single runner locally (Stage B)
epycloud run job --local --stage runner --exp-id test-sim --run-id <run_id> --task-index 0

# Run multiple runners for different tasks
for i in {0..9}; do
  epycloud run job --local --stage runner --exp-id test-sim --run-id <run_id> --task-index $i &
done
wait

# Run output generation (Stage C)
epycloud run job --local --stage output --exp-id test-sim --run-id <run_id> --num-tasks 10
```

**Note:** The `epycloud` CLI wraps `docker compose` calls with additional features:
- Automatically includes `--rm` flag to remove containers after execution (prevents orphaned containers)
- Validates required environment variables (e.g., `EXP_ID`, `RUN_ID`)
- Passes environment variables to docker compose: `EXP_ID`, `RUN_ID`, `TASK_INDEX`, `NUM_TASKS`
- Provides helpful output messages showing where files are read/written

**What the epycloud CLI does:**
- `epycloud run job --local --stage builder` → runs `docker compose run --rm builder` with environment variables
- `epycloud run job --local --stage runner` → runs `docker compose run --rm runner` with environment variables
- `epycloud run job --local --stage output` → runs `docker compose run --rm output` with environment variables

**Alternative (NOT recommended): Direct docker compose commands**
```bash
# If you must run docker compose directly, always include --rm
docker compose run --rm builder
TASK_INDEX=0 docker compose run --rm runner
docker compose run --rm output
```

#### Docker Compose configuration

The Docker Compose setup (defined in [docker-compose.yml](../docker-compose.yml)):

**Volume bindings:**
- Mounts `./local` (host) to `/data` (container)
  - `./local/bucket/` → `/data/bucket/` - Simulates GCS bucket for builder-artifacts/runner-artifacts
  - `./local/forecast/` → `/data/forecast/` - Forecast repository data (alternative to git clone)

**Configuration:**
- Uses the `local` build target (smaller image, no gcloud CLI)
- Loads environment variables from `.env.local` (optional, for GitHub PAT)
- Sets `EXECUTION_MODE=local` automatically (enables local filesystem instead of GCS)
- Environment variables: `EXP_ID`, `RUN_ID`, `TASK_INDEX`

**Services:**
- **dispatcher** - Runs `run_builder.sh` to generate input files
- **runner** - Runs `main_runner.py` to process individual tasks

**Local directory structure:**
```
./local/                    # Host directory (mounted as /data in container)
  bucket/                   # → /data/bucket/ (simulates GCS bucket)
    {exp_id}/
      {run_id}/
        builder-artifacts/  # Generated input files (input_0000.pkl, ...)
        runner-artifacts/   # Simulation results (result_0000.pkl, ...)
  forecast/                 # → /data/forecast/ (forecast repository)
    experiments/            # YAML experiment configurations
```

The storage abstraction layer in the scripts automatically detects `EXECUTION_MODE=local` and uses `/data/bucket/` instead of `gs://bucket-name/`. See [local-docker-design.md](local-docker-design.md) for implementation details.


## 7) Scripts

### Stage A Wrapper: [scripts/run_builder.sh](scripts/run_builder.sh)

Shell wrapper that handles forecast repository setup before running the dispatcher.

**Features:**
- **Cloud mode**: Fetches GitHub PAT from Secret Manager and clones forecast repo
- **Local mode**: Uses mounted forecast data from `/data/forecast`
- Adds forecast data to `PYTHONPATH`
- Supports optional `FORECAST_REPO_REF` for branch/tag checkout (cloud only)

**Environment variables:**
- `EXECUTION_MODE` - "cloud" or "local" (required)
- `GITHUB_FORECAST_REPO` - Forecast repo to clone (cloud mode only)
- `FORECAST_REPO_DIR` - Where to clone repo (default: `/data/forecast/`, cloud only)
- `GCLOUD_PROJECT_ID` - GCP project for Secret Manager (cloud mode only)
- `GITHUB_PAT_SECRET` - Secret Manager secret name (default: `github-pat`, cloud only)
- `FORECAST_REPO_REF` - Optional branch/tag to checkout (cloud mode only)


### Stage A: [scripts/main_builder.py](scripts/main_builder.py)

Generates input files based on configuration and uploads them to GCS.

**Features:**
- Environment variables: `GCS_BUCKET`, `OUT_PREFIX`, `JOBID`, `EXP_ID`, `RUN_ID`
- Automatically discovers and resolves config files by parsing YAML structure
- Creates pickled input files with model configs
- Output pattern: `{OUT_PREFIX}input_{i:04d}.pkl`
- Logging for monitoring progress

**Usage:**
```bash
python main_builder.py
```

### Stage B: [scripts/main_runner.py](scripts/main_runner.py)

Processes individual tasks in parallel using `BATCH_TASK_INDEX`.

**Features:**
- Environment variables: `BATCH_TASK_INDEX`, `GCS_BUCKET`, `IN_PREFIX`, `OUT_PREFIX`
- Downloads input: `{IN_PREFIX}input_{idx:04d}.pkl`
- Runs simulation (currently placeholder logic)
- Uploads results: `{OUT_PREFIX}result_{idx:04d}.pkl`
- Error handling and logging

**Note:** `BATCH_TASK_INDEX` is automatically set by Cloud Batch (0-indexed).

### Stage C: [scripts/main_output.py](scripts/main_output.py)

Aggregates all Stage B results and generates formatted CSV outputs.

**Features:**
- Environment variables: `GCS_BUCKET`, `EXP_ID`, `RUN_ID`, `NUM_TASKS`
- Downloads all result files: `{RUN_ID}/runner-artifacts/result_*.pkl`
- Automatically discovers output configuration from experiment directory
- Generates formatted CSV outputs (quantiles, trajectories, posteriors, metadata)
- Uploads to: `{RUN_ID}/outputs/*.csv.gz`
- Error handling for missing result files

**Wrapper:** [scripts/run_output.sh](scripts/run_output.sh)
- Similar to `run_builder.sh`, handles cloud vs local mode
- No repo cloning needed (uses already-installed epymodelingsuite)



## 8) Monitoring and Resource Groups

The infrastructure uses **resource labels** to organize and monitor different stages of the pipeline. All resources are tagged with labels for easy filtering and monitoring.

### Label Structure

All resources use a consistent labeling scheme:
- **`component: epymodelingsuite`** - Identifies all resources belonging to this system
- **`stage`** - Identifies the specific phase:
  - `imagebuild` - Cloud Build jobs that build Docker images
  - `builder` - Stage A Batch jobs (dispatcher that generates input files)
  - `runner` - Stage B Batch jobs (parallel simulation runners)
  - `output` - Stage C Batch jobs (output aggregation and formatting)
- **`exp_id`** - Dynamic label for experiment ID (Batch jobs only)
- **`run_id`** - Dynamic label for workflow execution/run ID (Batch jobs only)
- **`environment: production`** - Environment identifier
- **`managed-by`** - Shows which tool manages the resource (`terraform`, `cloudbuild`, `workflows`)

### Monitoring Dashboards

After running `make tf-apply`, three Cloud Monitoring dashboards are automatically created:

1. **Builder Dashboard** - Monitors Stage A (builder) CPU/memory usage
   - Filter: `component=epymodelingsuite AND stage=builder`
   - Metrics: CPU %, Memory %, Memory MiB, CPU cores

2. **Runner Dashboard** - Monitors Stage B (parallel runners) CPU/memory, parallelism
   - Filter: `component=epymodelingsuite AND stage=runner`
   - Metrics: CPU %, Memory %, Memory MiB, CPU cores, Active instances

3. **Output Dashboard** - Monitors Stage C (output generation) CPU/memory usage
   - Filter: `component=epymodelingsuite AND stage=output`
   - Metrics: CPU %, Memory %, Memory MiB, CPU cores

4. **Overall System Dashboard** - Monitors all stages combined
   - Filter: `component=epymodelingsuite`
   - Metrics: Aggregated CPU/memory by stage, Active instances by stage

**Access dashboards:**
```bash
# After terraform apply, get dashboard URLs:
epycloud terraform output | grep dashboard
```

Or navigate to: [Cloud Console → Monitoring → Dashboards](https://console.cloud.google.com/monitoring/dashboards)

### Custom Filtering

You can create custom queries in Cloud Monitoring to filter by specific experiments or runs:

```
# View all resources for a specific experiment
component=epymodelingsuite AND exp_id="experiment-01"

# View specific run of an experiment
component=epymodelingsuite AND run_id="abc123-def456"

# Compare builder vs runner performance
component=epymodelingsuite AND (stage=builder OR stage=runner)
```


## 9) epycloud CLI

The `epycloud` CLI provides all operational commands for the pipeline. For detailed commands and workflows, see [/docs/operations.md](/docs/operations.md).


**Quick reference:**

```bash
# Infrastructure
epycloud terraform init        # Initialize Terraform
epycloud terraform plan        # Preview changes
epycloud terraform apply       # Deploy infrastructure
epycloud terraform destroy     # Destroy resources
epycloud terraform output      # View Terraform outputs

# Build
epycloud build cloud           # Cloud Build (recommended)
epycloud build local           # Build locally and push
epycloud build dev             # Build for local development
epycloud build status          # Check build status

# Execute (Cloud)
epycloud run workflow --exp-id my-exp   # Run workflow on cloud

# Monitor
epycloud status                         # Quick status check
epycloud workflow list                  # List workflows
epycloud workflow list --exp-id my-exp  # Filter by experiment
epycloud workflow describe <id>         # Workflow details
epycloud logs --exp-id my-exp           # View logs
epycloud logs --exp-id my-exp --stage B # Filter by stage

# Local development
epycloud run job --local --stage builder --exp-id test-sim
epycloud run job --local --stage runner --exp-id test-sim --run-id <run_id> --task-index 0
epycloud run job --local --stage output --exp-id test-sim --run-id <run_id> --num-tasks 10

# Configuration
epycloud config show           # Show current config
epycloud config edit           # Edit configuration
epycloud config validate       # Validate configuration
```


## 10) Operational notes

* **Reproducibility**: tag images with immutable digests and store a `run_metadata.json` next to outputs (image digest, args, run time, counts).
* **Quotas**:
  - Cap `parallelism` in Workflows (default: 100, configurable via `MAX_PARALLELISM` in `.env`)
  - Cloud Batch supports up to 5,000 parallel tasks per job
  - Adjust CPU/Memory per task based on your region's vCPU quota
  - **Avoid queueing**: Set explicit `STAGE_B_MACHINE_TYPE` with `TASK_COUNT_PER_NODE=1` for predictable VM provisioning
* **VM Allocation Best Practices**:
  - **Set `TASK_COUNT_PER_NODE=1`** for parallel execution (one task per VM)
  - **Set explicit `STAGE_B_MACHINE_TYPE`** (e.g., "c4d-standard-2") for predictable scaling
  - **Match `STAGE_B_CPU_MILLI` to machine capacity**: `c4d-standard-2` (2 vCPU) → `CPU_MILLI=2000`
  - Monitor first job run in Cloud Console to verify expected number of VMs are created
* **Security**:
  - Principle of least privilege (scoped IAM on bucket, read-only PAT for repos)
  - Only unpickle **trusted** data produced by Stage A
  - GitHub authentication via fine-grained PAT with minimal permissions (Contents: read)
  - **Never commit GitHub PAT** - stored in Secret Manager only
  - Rotate PAT regularly and set appropriate expiration dates

## 11) Billing and Cost Tracking

All resources are labeled with `component=epymodelingsuite` for billing tracking.

**View costs in GCP Console:**
1. Go to **Billing → Reports**
2. Add filter: **Labels → component = epymodelingsuite**
3. Group by: **Service** (to see Cloud Build, Batch, Workflows, etc.)

**Billable resources tracked:**
- Cloud Build (image builds)
- Cloud Batch (compute for jobs)
- Cloud Workflows (orchestration)
- Artifact Registry (Docker image storage)
- Secret Manager (GitHub PAT storage)
- Cloud Logging (inherited from parent resources)

**Note:** Cloud Storage costs are not tracked by labels since the bucket is shared with other projects. Track storage by prefix (`DIR_PREFIX`) if needed.

## 12) Implementation Summary


**📝 TODO (for production use):**
- Set up result aggregation/analysis scripts
- Configure monitoring and alerting for workflow failures
- Implement result validation and quality checks

