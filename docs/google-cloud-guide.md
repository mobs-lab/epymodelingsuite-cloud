# Batch + Workflows Pipeline

This document includes information of the **Cloud Batch + Workflows** pipeline using Terraform, Docker images, and lightweight scripts.

---

## 0) Design and architecture

* **Infrastructure-as-code (Terraform)** for:
  * Artifact Registry (container repo)
  * GCS buckets/prefixes (inputs/results, optional logs)
  * Service Accounts & IAM (Workflows runner, Batch runtime)
  * Workflows (deployed from YAML)
* **Container image** (Dockerfile + requirements) with both Stage A / Stage B entrypoints
* **Scripts**:
  * `run_dispatcher.sh` (Setups and runs stage A).
  * `main_dispatcher.py` (Stage A: produce N pickled inputs)
  * `main_runner.py` (Stage B: consume one pickle per task using `BATCH_TASK_INDEX`)
* **Workflow YAML**:
  * Orchestrates: Stage A → wait → list GCS → Stage B (`taskCount=N`) → wait
* **Makefile (optional)**: common commands (build/push/deploy/run)

---

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
│  └─ requirements.txt
├─ scripts/
│  ├─ main_dispatcher.py         # Stage A: Generate N input files
│  └─ main_runner.py             # Stage B: Process individual tasks
├─ jobs/                         # Manual job templates for testing/debugging
│  ├─ stage-a.json
│  ├─ stage-b.json
│  └─ README.md
├─ Makefile                      # Build/deploy automation
├─ cloudbuild.yaml               # Cloud Build configuration
├─ .env                          # Environment variables (gitignored)
├─ .env.example                  # Template for environment variables
├─ .gitignore
└─ README.md
```

---

## 2) Prerequisites

* gcloud authenticated to target project: `gcloud auth login`, `gcloud config set project <PROJECT_ID>`
* Terraform ≥ 1.5
* Docker
* Python 3.11 (for local dev)
* (Optional) `make`
* **GitHub Fine-Grained Personal Access Token (PAT)** - required for accessing private repositories (epymodelingsuite and forecasting)

Installing Terraform
```sh
# https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli
# Mac
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
 ```

### Permissions

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
export GITHUB_MODELING_SUITE_REPO=owner/flumodelingsuite  # Modeling suite package (format: owner/repo)
export GITHUB_MODELING_SUITE_REF=main  # Branch or commit to build from

# After editing, load the variables
source .env
```

**Note**: This implementation does not make a new bucket, but rather uses an **existing GCS bucket**.

### Setting up GitHub Personal Access Token

The pipeline requires a GitHub Fine-Grained Personal Access Token (PAT) to clone private repositories during Docker build and Batch job execution.

**Create a fine-grained PAT:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Set appropriate name and expiration
4. Under "Repository access", select "Only select repositories" and add:
   - `flumodelingsuite` repository (modeling suite package)
   - `flu-forecast-epydemix` repository (forecast data)
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

---

## 3) Terraform (core resources)

See full implementation in [terraform/main.tf](terraform/main.tf), [terraform/variables.tf](terraform/variables.tf), and [terraform/outputs.tf](terraform/outputs.tf).

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

---

## 4) Workflow YAML

See full implementation in [terraform/workflow.yaml](terraform/workflow.yaml).

**Orchestration flow:**
1. **Stage A (Generator)**: Single Batch job that runs `main_dispatcher.py` to generate N input files
2. **List inputs**: Counts generated files in GCS
3. **Stage B (Runner)**: Parallel Batch jobs (N tasks) running `main_runner.py`, each processing one input
4. **Wait helper**: Polls Batch job status until completion

**Key features:**
- Takes runtime parameters: `count`, `seed`, `bucket`, `dirPrefix`, `sim_id`, `batchSaEmail`, `githubForecastRepo`, `maxParallelism` (optional, default: 100)
- Auto-generates `run_id` from workflow execution ID for unique identification
- Constructs paths: `{dirPrefix}{sim_id}/{run_id}/inputs/` and `/results/`
- Stage A: 2 CPU, 4 GB RAM, includes repo cloning via [run_dispatcher.sh](scripts/run_dispatcher.sh)
- Stage B: 2 CPU, 8 GB RAM, configurable parallelism (default: 100, max: 5000 per Cloud Batch limits)
- GitHub authentication via PAT from Secret Manager
- Logs to Cloud Logging
- Error handling for failed/deleted jobs
- Returns job names and task count

---

## 5) Compute Resources and Instance Types

### Understanding cpuMilli

In Google Cloud Batch, compute resources are specified using `cpuMilli` and `memoryMib` rather than predefined instance types (which are also available as options).

**cpuMilli** represents thousandths of a vCPU:
- `1000 cpuMilli = 1 vCPU`
- `2000 cpuMilli = 2 vCPUs`
- `500 cpuMilli = 0.5 vCPU`

Google Cloud automatically provisions the appropriate machine type based on your resource requirements. You can optionally specify instances types. See [documentation](https://cloud.google.com/batch/docs/create-run-job#resources) for details.

### Current Resource Allocation

**Cloud Build** - [cloudbuild.yaml:22](../cloudbuild.yaml#L22)
```yaml
machineType: E2_MEDIUM
```
- [Predefined instance type](https://cloud.google.com/build/pricing?hl=en) for build operations. Note that the only options for CloudBuild are `e2-medium`, `e2-standard-2`, `e2-highcpu-8`, and `e2-highcpu-32`. See documentation for details.
- `e2-medium`: 1 vCPU, 4 GB RAM

**Stage A Job (Generator)** - [terraform/workflow.yaml:66-68](../terraform/workflow.yaml#L66-L68)
```yaml
computeResource:
  cpuMilli: 2000    # 2 vCPUs
  memoryMib: 4096   # 4 GB RAM
```
- Single task that generates input files
- Resources allocated: 2 vCPUs, 4 GB RAM

**Stage B Job (Runner)** - [terraform/workflow.yaml:139-141](../terraform/workflow.yaml#L139-L141)
```yaml
computeResource:
  cpuMilli: 2000    # 2 vCPUs
  memoryMib: 8192   # 8 GB RAM
```
- Parallel tasks processing individual simulations
- Resources allocated: 2 vCPUs, 8 GB RAM per task
- Higher memory allocation for simulation workload

### Tuning Compute Resources

To adjust resources for your workload, edit [terraform/workflow.yaml](../terraform/workflow.yaml):

**Example configurations:**
```yaml
# Lightweight tasks
computeResource:
  cpuMilli: 1000    # 1 vCPU
  memoryMib: 2048   # 2 GB

# Standard tasks (current)
computeResource:
  cpuMilli: 2000    # 2 vCPUs
  memoryMib: 8192   # 8 GB

# Compute-intensive tasks
computeResource:
  cpuMilli: 4000    # 4 vCPUs
  memoryMib: 16384  # 16 GB

# High-memory tasks
computeResource:
  cpuMilli: 8000    # 8 vCPUs
  memoryMib: 32768  # 32 GB
```

**Important notes:**
- Resource limits depend on your project's regional quotas
- Higher resources = higher costs per task
- Monitor actual resource usage with Cloud Logging to optimize allocation
- Google Cloud Batch supports up to 32 vCPUs and 128 GB per task

**After modifying resources:**
```bash
make tf-plan    # Review changes
make tf-apply   # Deploy updated configuration
```

---

## 6) Docker image

See [docker/Dockerfile](docker/Dockerfile) and [docker/requirements.txt](docker/requirements.txt).

**Multi-stage build architecture:**

The Dockerfile uses multi-stage builds with three stages:
1. **base** - Common dependencies (Python packages, uv, scripts, git, flumodelingsuite)
2. **local** - Minimal image for local development (base + no gcloud)
3. **cloud** - Full image with gcloud CLI for Secret Manager access

**Stage comparison:**
- **local**: ~300-400 MB, includes Python deps, git, scripts, and flumodelingsuite
- **cloud**: ~500-700 MB, adds gcloud CLI for Secret Manager access

Both stages include the flumodelingsuite package since it's needed for the actual modeling work.

**Current implementation (cloud stage):**
- Base: `python:3.11-slim`
- Installs git and gcloud CLI for Secret Manager access
- Uses `uv` for fast dependency management (10-100x faster than pip)
- Installs `google-cloud-storage` and other dependencies
- **Clones and installs flumodelingsuite package** from private GitHub repository (if configured)
- Copies scripts from [scripts/](scripts/) directory
- Default entrypoint: `main_dispatcher.py` (Stage A)

**Current configuration:**
- Image name: `epymodelingsuite` (configurable via `IMAGE_NAME` in [.env](.env))
- Image tag: `latest` (configurable via `IMAGE_TAG`)
- Full path: `${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/epymodelingsuite:latest`

**Build & push:**

```bash
# Option 1: Cloud Build (recommended for production)
make build

# Option 2: Build cloud image locally and push to Artifact Registry
source .env && gcloud auth configure-docker ${REGION}-docker.pkg.dev --project=${PROJECT_ID}
source .env.local  # For GITHUB_PAT
make build-local

# Option 3: Build local dev image (for Docker Compose, no push)
source .env.local  # For GITHUB_PAT
make build-dev

# Or manually with Cloud Build
gcloud builds submit --region ${REGION} --config cloudbuild.yaml
```

**Build target comparison:**
- `make build` - Uses Cloud Build on GCP, builds `cloud` target, pushes to Artifact Registry
- `make build-local` - Builds `cloud` target locally, pushes to Artifact Registry (requires auth)
- `make build-dev` - Builds `local` target locally, tags as `epymodelingsuite:local`, no push

**Local secrets management:**
- Create [.env.local](.env.local) (gitignored) for sensitive values like `GITHUB_PAT`
- Template available at [.env.local.example](.env.local.example)
- Required for `build-local` and `build-dev` with private repositories
- Cloud builds use Secret Manager instead

Cloud Build configuration in [cloudbuild.yaml](cloudbuild.yaml):
- Uses `E2_MEDIUM` machine type
- Logs to Cloud Logging only
- Automatically pushes to Artifact Registry
- **Fetches GitHub PAT from Secret Manager** for private repository access
- Passes `GITHUB_MODELING_SUITE_REPO` and `GITHUB_MODELING_SUITE_REF` as build arguments

**How flumodelingsuite is installed:**

The [Dockerfile](docker/Dockerfile) includes logic to clone and install the flumodelingsuite package during build:

```dockerfile
ARG GITHUB_MODELING_SUITE_REPO
ARG GITHUB_MODELING_SUITE_REF=main
ARG GITHUB_PAT

# Clone the flumodelingsuite repository and install it
RUN if [ -n "$GITHUB_MODELING_SUITE_REPO" ] && [ -n "$GITHUB_PAT" ]; then \
    git clone --branch ${GITHUB_MODELING_SUITE_REF} \
        https://${GITHUB_PAT}@github.com/${GITHUB_MODELING_SUITE_REPO}.git /tmp/flumodelingsuite && \
    cd /tmp/flumodelingsuite && \
    uv pip install --system --no-cache . && \
    cd /app && \
    rm -rf /tmp/flumodelingsuite; \
    fi
```

**Key features:**
- Installs at **build time** (baked into the Docker image)
- Uses GitHub PAT from Secret Manager (Cloud Build) or environment variable (local)
- Supports specific branch/commit via `GITHUB_MODELING_SUITE_REF`
- Repository is removed after installation to keep image clean
- PAT is not persisted in image layers

**Two repository patterns:**
1. **flumodelingsuite** (`GITHUB_MODELING_SUITE_REPO`) - Installed at build time inside the Docker image
2. **flu-forecast-epydemix** (`GITHUB_FORECAST_REPO`) - Cloned at runtime by [run_dispatcher.sh](scripts/run_dispatcher.sh)

**Local development with Docker Compose:**

For local development, first build the local image, then use the Makefile commands:

```bash
# Build local development image
source .env.local  # For GITHUB_PAT if using private repos
make build-dev

# Run dispatcher
make run-dispatcher-local

# Run a single runner locally
TASK_INDEX=0 make run-runner-local

# Run multiple runners for different tasks
for i in {0..9}; do
  TASK_INDEX=$i make run-runner-local &
done
wait
```

**Note:** Using the Makefile commands (`make run-dispatcher-local` or `make run-runner-local`) is recommended instead of running `docker compose` directly. The Makefile automatically includes the `--rm` flag to avoid orphan containers.

**Alternative (NOT recommended): Direct docker compose commands**
```bash
# If you must run docker compose directly, always include --rm
docker compose run --rm dispatcher
TASK_INDEX=0 docker compose run --rm runner
```

The Docker Compose setup:
- Uses the `local` build target (smaller, no gcloud)
- Mounts `./local/bucket` to `/data/bucket` for GCS bucket simulation
- Mounts `./local/forecast` to `/data/forecast` for forecast data
- Loads additional config from `.env.local` (optional)
- Sets `EXECUTION_MODE=local` automatically (requires storage abstraction layer - see [local-docker-design.md](local-docker-design.md))

**Local directory structure:**
```
./local/
  bucket/           # Simulates GCS bucket (inputs/outputs)
    {sim_id}/
      {run_id}/
        inputs/     # Generated input files
        results/    # Simulation results
  forecast/         # Forecast repository data (alternative to git clone)
```

---

## 7) Scripts

### Stage A Wrapper: [scripts/run_dispatcher.sh](scripts/run_dispatcher.sh)

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

**Usage (cloud):**
```bash
export EXECUTION_MODE=cloud
export GITHUB_FORECAST_REPO=owner/repo
export GCLOUD_PROJECT_ID=your-project
./run_dispatcher.sh
```

**Usage (local):**
```bash
export EXECUTION_MODE=local
# Place forecast data in ./local/forecast/
./run_dispatcher.sh
```

### Stage A: [scripts/main_dispatcher.py](scripts/main_dispatcher.py)

Generates input files based on configuration and uploads them to GCS.

**Features:**
- Environment variables: `GCS_BUCKET`, `OUT_PREFIX`, `JOBID`, `SIM_ID`, `RUN_ID`
- Automatically discovers and resolves config files by parsing YAML structure
- Creates pickled input files with model configs
- Output pattern: `{OUT_PREFIX}input_{i:04d}.pkl`
- Logging for monitoring progress

**Usage:**
```bash
python main_dispatcher.py
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


---

## 8) Makefile

See full implementation in [Makefile](Makefile).

**Available commands:**
- `make help` - Show all commands and current configuration
- `make build` - Build and push with Cloud Build
- `make build-local` - Build locally and push
- `make tf-init` - Initialize Terraform
- `make tf-plan` - Preview Terraform changes
- `make tf-apply` - Apply infrastructure
- `make tf-destroy` - Destroy all resources (5-second safety delay)
- `make run-workflow` - Execute the pipeline
- `make clean` - Clean local artifacts

**Configuration:**
- Reads from environment variables (source `.env` first)
- `run-workflow` auto-retrieves Batch SA email from Terraform
- Configurable: `RUN_COUNT`, `RUN_SEED`

**Quick workflow:**
```bash
source .env
make tf-init
make tf-apply
make build
make run-workflow
```

---

## 9) Operational notes

* **Reproducibility**: tag images with immutable digests and store a `run_metadata.json` next to outputs (image digest, args, run time, counts).
* **Quotas**: cap `parallelism` in Workflows (default: 100, configurable via `maxParallelism` parameter, Cloud Batch supports up to 5,000 parallel tasks per job); adjust CPU/Memory per task based on your region's vCPU quota.
* **Retries**: design `main_runner.py` to be idempotent (safe to rerun a failed task). Consider writing to a temp key then atomic rename.
* **Security**:
  - Principle of least privilege (scoped IAM on bucket, read-only PAT for repos)
  - Only unpickle **trusted** data produced by Stage A
  - GitHub authentication via fine-grained PAT with minimal permissions (Contents: read)
  - **Never commit GitHub PAT** - stored in Secret Manager only
  - `.env` and `terraform.tfvars` are gitignored
  - Rotate PAT regularly and set appropriate expiration dates
* **Local test**: Run scripts locally by exporting environment variables:
  ```bash
  export BATCH_TASK_INDEX=0 GCS_BUCKET=your-bucket
  python scripts/main_runner.py
  ```
* **Manual job execution**: Use templates in [jobs/](jobs/) directory for testing individual stages
* **UV benefits**: 10-100x faster installs, better caching, smaller image layers

---

## 10) Quick start

```bash
# 1) Set up environment variables
cp .env.example .env
# Edit .env with your project details
source .env

# 2) Create GitHub PAT and store in Secret Manager
echo -n "your_github_pat_here" | gcloud secrets create github-pat \
  --data-file=- \
  --project=${PROJECT_ID}

# 3) Initialize and apply Terraform
make tf-init
make tf-plan    # Review changes first
make tf-apply

# 4) Build & push Docker image
make build

# 5) Run the workflow
make run-workflow

# 6) Monitor execution
gcloud workflows executions list epydemix-pipeline --location=$REGION

# 7) Check logs and details
gcloud workflows executions describe <execution_id> \
  --workflow=epydemix-pipeline --location=$REGION

# View Batch job logs
gcloud logging read "resource.type=batch.googleapis.com/Job" --limit 50
```

---

## 11) Implementation Summary

**✅ Completed:**
- Full Terraform infrastructure in [terraform/](terraform/)
- Docker configuration with `uv` in [docker/](docker/)
- **Private repository support** - flumodelingsuite installed at build time, forecast data cloned at runtime
- Python scripts in [scripts/](scripts/)
- Workflows orchestration in [terraform/workflow.yaml](terraform/workflow.yaml)
- Makefile automation in [Makefile](Makefile)
- Manual job templates in [jobs/](jobs/)
- Environment configuration ([.env.example](.env.example), [.gitignore](.gitignore))
- Documentation ([README.md](README.md), [docs/variable-configuration.md](docs/variable-configuration.md))
- GitHub authentication via Secret Manager
- Replace placeholder in [scripts/main_runner.py](scripts/main_runner.py):62 with actual epydemix model code

**📝 TODO (for production use):**
- Tune compute resources in [terraform/workflow.yaml](terraform/workflow.yaml) based on actual workload
- Set up result aggregation/analysis scripts
- Configure monitoring and alerting for workflow failures
- Implement result validation and quality checks

