# Operations Guide

This document covers common operational commands for running and monitoring the pipeline.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Reference](#quick-reference)
- [Building Docker Images](#building-docker-images)
  - [Build Targets](#build-targets)
  - [Cloud Build (Recommended for Production)](#cloud-build-recommended-for-production)
  - [Local Build and Push](#local-build-and-push)
  - [Local Development Build](#local-development-build)
- [Running the Pipeline](#running-the-pipeline)
  - [A) Cloud Execution](#a-cloud-execution)
  - [B) Local Execution](#b-local-execution)
- [Monitoring](#monitoring)
  - [Workflow Executions](#workflow-executions)
  - [Batch Jobs](#batch-jobs)
  - [Cloud Storage](#cloud-storage)
  - [Logs](#logs)
  - [Cloud Console Dashboards](#cloud-console-dashboards)
- [Terraform Operations](#terraform-operations)
  - [Initialize Terraform](#initialize-terraform)
  - [Preview Changes](#preview-changes)
  - [Apply Infrastructure Changes](#apply-infrastructure-changes)
  - [Destroy Infrastructure](#destroy-infrastructure)
  - [Update Docker Image](#update-docker-image)

## Prerequisites

Before running any commands, load your environment configuration:

```bash
# Load primary configuration (required)
source .env

# For local Docker builds with private repos, also load local secrets
source .env.local
```

**Note:** Most `make` commands require environment variables from `.env`. Always run `source .env` first in a new terminal session.

## Quick Reference

```bash
# Load configuration
source .env

# ===============================================================
#        Only required for initial setup / updating setup
# ===============================================================
# Deploy infrastructure
# make tf-init && make tf-apply

# Build Docker image
# make build
# ===============================================================

# ========================== Production =========================
# 0. Add experiments (YAML files) in forecast repository. Make sure to git push.
# 1. Run workflow on cloud
EXP_ID=experiment-01 make run-workflow

# 2. Monitor workflow
gcloud workflows executions list epydemix-pipeline --location=$REGION

# ======================= Testing locally ========================
# 0. Setup local experiment configs in ./local/forecast/experiments/{EXP_ID}/config/

# 1. Test pipeline locally with Docker Compose
source .env && source .env.local
# Build Docker image for local testing
make build-dev
# You need to specify RUN_ID manually for local runs. It can have any arbitrary name, but we'll use "run-YYYYmmdd-hhmmss" for this example.
EXP_ID=test-sim RUN_ID=run-$(date +%Y%m%d-%H%M%S) make run-builder-local
EXP_ID=test-sim TASK_INDEX=0 make run-task-local
# Generate outputs
NUM_TASKS=1 make run-output-local
```

---

## Building Docker Images

The pipeline runs in Docker containers. You can build images using Cloud Build (recommended for production) or locally for development and testing.

### Build Targets
There are three build targets:
- `make build` - Cloud Build, pushed to Artifact Registry.
- `make build-local` - Local build, pushed to Artifact Registry.
- `make build-dev` - Development build for locally testing pipeline. Doesn't get pushed to cloud.

### Cloud Build (Recommended for Production)

Build and push Docker image using Google Cloud Build:

```bash
# Load configuration
source .env

# Build image on cloud
make build
```

This uses the cloud infrastructure and automatically pushes to Artifact Registry.

### Local Build and Push

Build locally and push to Artifact Registry:

```bash
# Load both configurations
source .env
source .env.local  # For GITHUB_PAT

# Authenticate Docker (one-time setup)
gcloud auth configure-docker ${REGION}-docker.pkg.dev --project=${PROJECT_ID}

# Build and push
make build-local
```

### Local Development Build

To run the pipeline locally, you will need a local development build image:

```bash
# Load both configurations
source .env
source .env.local  # For GITHUB_PAT (if using private repos)

# Build local dev image
make build-dev
```



## Running the Pipeline

The pipeline can be executed on Google Cloud for production runs or locally using Docker for development and testing.

### A) Cloud Execution

Run the full pipeline on Google Cloud:

```bash

# Add experiments (YAML files) in forecast repository. Make sure to git push.

# Load configuration
source .env

# Basic run
EXP_ID=my-experiment make run-workflow

# The workflow will:
# 1. Generate a unique RUN_ID automatically
# 2. Run Stage A (builder) to create input files
# 3. Run Stage B (runners) in parallel
# 4. Run Stage C (output) to aggregate results and generate CSV outputs
# 5. Store results in: gs://{bucket}/{DIR_PREFIX}{EXP_ID}/{RUN_ID}/
```

**Customization:**
```bash
# Add experiments (YAML files) in forecast repository. Make sure to git push.

# Load configuration
source .env

# Override specific values by passing environment variables
EXP_ID=experiment-01 \
DIR_PREFIX=custom/path/ \
make run-workflow
```

**Rerunning a single failed task:**

When a specific task in stage B failed, you can trigger a rerun for that task:

```bash
# Run task 3 from an existing run
EXP_ID=test-flu \
RUN_ID=20251017-0145-xxxxxx \
TASK_INDEX=3 \
make run-task-cloud
```

This submits a single-task Batch job for debugging purposes.

**Running Stage C independently:**

If Stage C fails or you want to regenerate outputs:

```bash
# Run output generation for an existing run
EXP_ID=test-flu \
RUN_ID=20251017-0145-xxxxxx \
NUM_TASKS=10 \
make run-output-cloud
```

Note: All Stage B tasks must have completed successfully before running Stage C. The output configuration is automatically discovered from the experiment directory.


### B) Local Execution

Run the pipeline locally for testing using Docker.

#### Overview

**Key differences from cloud mode:**

- Storage: Uses `./local/` directory instead of Google Cloud Storage (GCS)
- Forecast repo: Reads from `./local/forecast/` instead of cloning from GitHub
- RUN_ID: Must be set manually (not auto-generated)

**Local directory structure:**

```
./local/
  bucket/                    # Simulates GCS bucket (created automatically)
    {EXP_ID}/{RUN_ID}/
      builder-artifacts/input_*.pkl     # Generated by builder
      runner-artifacts/result_*.pkl     # Generated by runners
      outputs/*.csv.gz                  # Generated by output stage
  forecast/                  # Experiment configurations
    experiments/{EXP_ID}/config/*.yaml
    experiments/{EXP_ID}/config/output.yaml  # Output configuration
```

#### Setup

**One-time setup:**

```bash
# 1. Configure environment files
cp .env.example .env && cp .env.local.example .env.local
# Edit both files (set GITHUB_PAT in .env.local for building the Docker image)

# 2. Load environment
source .env && source .env.local

# 3. Create experiment directory
mkdir -p ./local/forecast/experiments/{EXP_ID}/config/
# Add config files: at minimum basemodel.yaml (optional: sampling.yaml, calibration.yaml)

# 4. Build local development image (takes a few minutes)
make build-dev
```

#### Running an Experiment

```bash
# 1. Set experiment ID and generate unique RUN_ID
export EXP_ID=test-sim
export RUN_ID=run-$(date +%Y%m%d-%H%M%S)

# 2. Run builder (Stage A)
EXP_ID=$EXP_ID RUN_ID=$RUN_ID make run-builder-local
ls -R ./local/bucket/$EXP_ID/$RUN_ID/builder-artifacts/  # Verify: should show input_*.pkl files

# 3. Run tasks (Stage B)
# Single task:
EXP_ID=$EXP_ID RUN_ID=$RUN_ID TASK_INDEX=0 make run-task-local

# Or multiple in parallel:
for i in {0..9}; do
  EXP_ID=$EXP_ID RUN_ID=$RUN_ID TASK_INDEX=$i make run-task-local &
done
wait

ls ./local/bucket/$EXP_ID/$RUN_ID/runner-artifacts/  # Verify: should show result_*.pkl files

# 4. Run output generation (Stage C)
# First, determine NUM_TASKS from the number of result files
export NUM_TASKS=$(ls ./local/bucket/$EXP_ID/$RUN_ID/runner-artifacts/result_*.pkl | wc -l)

EXP_ID=$EXP_ID RUN_ID=$RUN_ID NUM_TASKS=$NUM_TASKS make run-output-local

ls ./local/bucket/$EXP_ID/$RUN_ID/outputs/  # Verify: should show *.csv.gz files
```

**Important:** Always set a unique `RUN_ID` for each run (e.g., `run-$(date +%Y%m%d-%H%M%S)`), otherwise it defaults to "unknown" and overwrites previous data. All local data is stored in `./local/bucket/{EXP_ID}/{RUN_ID}/`.


## Monitoring

Monitor pipeline execution using Google Cloud Console dashboards, command-line tools, and logs.

### Workflow Executions

https://console.cloud.google.com/workflows

List recent workflow runs:

```bash
gcloud workflows executions list epydemix-pipeline --location=$REGION
```

Get details of a specific execution:

```bash
gcloud workflows executions describe <execution-id> \
  --workflow=epydemix-pipeline \
  --location=$REGION
```

### Batch Jobs

https://console.cloud.google.com/batch

List batch jobs:

```bash
gcloud batch jobs list --location=$REGION
```

Get job details:

```bash
gcloud batch jobs describe <job-name> --location=$REGION
```

List tasks for a job:

```bash
gcloud batch tasks list --job=<job-name> --location=$REGION
```

### Cloud Storage

https://console.cloud.google.com/storage/browser


### Logs

https://console.cloud.google.com/logs/

View workflow logs:

```bash
gcloud logging read "resource.type=workflows.googleapis.com/Workflow" \
  --limit=50 \
  --format=json
```

View batch job logs:

```bash
gcloud logging read "resource.type=batch.googleapis.com/Job" \
  --limit=50
```

View logs for specific experiment:

```bash
gcloud logging read "labels.exp_id=experiment-01" --limit=50
```

Tail live logs:

```bash
gcloud logging tail "resource.type=batch.googleapis.com/Job"
```


### Cloud Console Dashboards

Access monitoring dashboards from [here](https://console.cloud.google.com/monitoring/dashboards).

Four dashboards are available:
- **Builder Dashboard** - Stage A (builder) metrics
- **Runner Dashboard** - Stage B (parallel runners) metrics
- **Output Dashboard** - Stage C (output generation) metrics
- **Overall System Dashboard** - Combined metrics across all stages


## Terraform Operations

Manage Google Cloud infrastructure using Terraform commands. All Terraform commands require `.env` to be loaded.

### Initialize Terraform

First-time setup:

```bash
source .env
make tf-init
```

### Preview Changes

See what will change before applying:

```bash
source .env
make tf-plan
```

### Apply Infrastructure Changes

Deploy or update infrastructure:

```bash
source .env
make tf-apply
```

**What gets created:**
- Artifact Registry repository
- Service accounts with IAM permissions
- Cloud Workflows definition
- Monitoring dashboards
- Secret Manager references

### Destroy Infrastructure

Remove all Terraform-managed resources:

```bash
source .env
make tf-destroy
```

**Warning:** This deletes all infrastructure except:
- GCS bucket (pre-existing, managed separately)
- Secret Manager secrets (requires manual deletion)
- Stored data in GCS

### Update Docker Image

After code changes:

```bash
# Load configuration
source .env

# 1. Build new image
make build

# 2. Run workflow (uses latest tag)
EXP_ID=updated-experiment make run-workflow
```

For versioned images:

```bash
# Edit .env and update IMAGE_TAG
# Then reload and rebuild
source .env

make build
make tf-apply  # Update workflow to reference new tag
```