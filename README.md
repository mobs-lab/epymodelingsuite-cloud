# Epymodelingsuite Google Cloud Pipeline

Serverless, scalable pipeline for running parallel epydemix simulations on Google Cloud using Cloud Batch + Workflows.

## Overview

This pipeline orchestrates two-stage simulation runs:
- **Stage A**: Generate N input configurations → GCS
- **Stage B**: Process N simulations in parallel → results to GCS
- **Orchestration**: Workflows coordinates stages with retry logic

**Key benefits:** Serverless, scales to 1000s of tasks, pay-per-use, infrastructure as code.

## Quick Start

For detailed setup instructions, see [/docs/google-cloud-guide.md](/docs/google-cloud-guide.md).

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your project details
source .env

# For local Docker builds with private repos, set up secrets
cp .env.local.example .env.local
# Edit .env.local with your GitHub PAT
source .env.local

# 2. Deploy infrastructure
make tf-init && make tf-apply

# 3. Build Docker image
make build        # Cloud build (recommended)
# OR
make build-local  # Build cloud image locally and push (requires .env.local with GITHUB_PAT)
# OR
make build-dev    # Build local dev image for Docker Compose (requires .env.local with GITHUB_PAT)

# 4a. Run pipeline on Google Cloud
make run-workflow

# Or customize cloud run:
EXP_ID=experiment-01 make run-workflow

# 4b. OR run locally with Docker Compose (use Makefile commands)
make build-dev                # Build local image first
make run-dispatcher-local     # Run dispatcher with defaults
make run-runner-local         # Run runner for single task (TASK_INDEX=0)

# Or customize local run:
EXP_ID=experiment-01 TASK_INDEX=5 make run-dispatcher-local

```



## Glossary

Understanding the key concepts and terminology used throughout this pipeline:

### Core Concepts

**Experiment (`EXP_ID`)**
- A logical grouping of related simulation runs
- Examples: `test-flu-calibration`, `sensitivity-analysis-2025`
- Used to organize outputs in GCS: `gs://{bucket}/{DIR_PREFIX}{EXP_ID}/`
- Remains constant across multiple runs of the same experiment

**Run (`RUN_ID`)**
- A single execution instance of an experiment
- Auto-generated with format: `YYYYMMDD-HHMMSS-{uuid-prefix}` (e.g., `20251017-143052-a1b2c3d4`)
- The uuid-prefix is the first 8 characters of the workflow execution ID
- Each run creates a unique directory: `gs://{bucket}/{DIR_PREFIX}{EXP_ID}/{RUN_ID}/`
- Allows multiple runs of the same experiment without overwriting results

**Workflow Execution**
- A single invocation of the Google Cloud Workflows orchestration
- Coordinates Stage A → Stage B → completion
- Generates a unique `RUN_ID` automatically
- One execution = one complete pipeline run
- Can be monitored via: `gcloud workflows executions describe <execution-id>`

### Pipeline Stages

**Stage A (Dispatcher/Builder)**
- Generates N input configuration files (pickled Python objects)
- Runs as a single Google Cloud Batch job with 1 task
- Outputs: `{EXP_ID}/{RUN_ID}/inputs/input_0000.pkl` through `input_{N-1}.pkl`
- Script: [scripts/main_dispatcher.py](scripts/main_dispatcher.py)

**Builder**
- Another name for Stage A or the dispatcher
- The component that "builds" or generates input configurations
- Labeled with `stage: builder` in Google Cloud resources

**Stage B (Runner)**
- Processes N simulations in parallel
- Runs as a single Google Cloud Batch job with N tasks
- Each task processes one input file (determined by `BATCH_TASK_INDEX`)
- Outputs: `{EXP_ID}/{RUN_ID}/results/result_0000.pkl` through `result_{N-1}.pkl`
- Script: [scripts/main_runner.py](scripts/main_runner.py)

**Runner**
- Another name for Stage B or individual simulation tasks
- The component that "runs" the actual simulations
- Labeled with `stage: runner` in Google Cloud resources

**Simulation**
- A single execution of the epydemix model with specific parameters
- Synonymous with "task" in this pipeline context
- Each simulation processes one input configuration file and produces one result file
- Example: Running 100 simulations = Stage B job with 100 tasks

### Google Cloud Batch Concepts

**Batch Job**
- A collection of related tasks submitted to Google Cloud Batch
- Contains: task count, resource requirements, container image, environment variables
- Examples: Stage A job (1 task), Stage B job (N tasks)
- Job lifecycle: QUEUED → SCHEDULED → RUNNING → SUCCEEDED/FAILED

**Task**
- A single unit of work within a Batch job
- Each task runs independently in its own container
- Identified by `BATCH_TASK_INDEX` (0-based)
- Stage A: 1 task (index 0)
- Stage B: N tasks (indices 0 to N-1)
- Tasks can run in parallel up to the `parallelism` limit

**Task Index (`TASK_INDEX` / `BATCH_TASK_INDEX`)**
- Zero-based integer identifying a specific task
- `BATCH_TASK_INDEX`: Automatically set by Cloud Batch (cloud execution)
- `TASK_INDEX`: Manually set for local execution via Docker Compose
- Used to determine which input file to process: `input_{TASK_INDEX:04d}.pkl`

**Parallelism**
- Maximum number of tasks that can run simultaneously
- Default: 100 (configurable via `MAX_PARALLELISM`)
- Google Cloud Batch limit: 5,000 parallel tasks per job
- Example: Job with 1,000 tasks and parallelism=100 → runs in ~10 batches

**Task Count**
- Total number of tasks in a Batch job
- Stage A: Always 1
- Stage B: Equals N (number of input files generated by Stage A)

### Execution Modes

**Cloud Execution**
- Runs on Google Cloud Batch
- Uses GCS for storage
- Environment: `EXECUTION_MODE=cloud`
- Commands: `make run-workflow`, `make run-task-cloud`

**Local Execution**
- Runs via Docker Compose on your machine
- Uses local filesystem (`./local/bucket/`)
- Environment: `EXECUTION_MODE=local`
- Commands: `make run-dispatcher-local`, `make run-task-local`


## Key Files & Documentation

- **[/docs/google-cloud-guide.md](/docs/google-cloud-guide.md)** - Complete implementation guide
- **[terraform/](terraform/)** - Infrastructure as code
  - [main.tf](terraform/main.tf) - Google Cloud resources
  - [workflow.yaml](terraform/workflow.yaml) - Orchestration logic
- **[scripts/](scripts/)** - Application code
  - [main_dispatcher.py](scripts/main_dispatcher.py) - Stage A generator
  - [main_runner.py](scripts/main_runner.py) - Stage B runner
  - [run_dispatcher.sh](scripts/run_dispatcher.sh) - Stage A wrapper for repo cloning
- **[docker/](docker/)** - Container config
  - [Dockerfile](docker/Dockerfile) - Multi-stage build (local and cloud targets)
- **[docker-compose.yml](docker-compose.yml)** - Local development setup
- **[Makefile](Makefile)** - Build/deploy automation
- **[/docs/variable-configuration.md](/docs/variable-configuration.md)** - Environment variable reference
- **[/docs/local-docker-design.md](/docs/local-docker-design.md)** - Local execution design

## Configuration

See [.env.example](.env.example), [.env.local.example](.env.local.example), and [/docs/variable-configuration.md](/docs/variable-configuration.md) for required environment variables.

**Configuration files:**
- [.env.example](.env.example) - Project configuration (copy to `.env`)
- [.env.local.example](.env.local.example) - Local secrets like GitHub PAT (copy to `.env.local`)
- Both `.env` and `.env.local` are gitignored for security

## Monitoring and Resource Groups

The infrastructure uses **resource labels** to organize and monitor different stages of the pipeline. All resources are tagged with labels for easy filtering and monitoring.

### Label Structure

All resources use a consistent labeling scheme:
- **`component: epymodelingsuite`** - Identifies all resources belonging to this system
- **`stage`** - Identifies the specific phase:
  - `imagebuild` - Cloud Build jobs that build Docker images
  - `builder` - Stage A Batch jobs (dispatcher that generates input files)
  - `runner` - Stage B Batch jobs (parallel simulation runners)
- **`exp_id`** - Dynamic label for experiment ID (Batch jobs only)
- **`run_id`** - Dynamic label for workflow execution/run ID (Batch jobs only)
- **`environment: production`** - Environment identifier
- **`managed-by`** - Shows which tool manages the resource (`terraform`, `cloudbuild`, `workflows`)

### Monitoring Dashboards

After running `make tf-apply`, three Cloud Monitoring dashboards are automatically created:

1. **Builder Dashboard** - Monitors Stage A (dispatcher) CPU/memory usage
   - Filter: `component=epymodelingsuite AND stage=builder`
   - Metrics: CPU %, Memory %, Memory MiB, CPU cores

2. **Runner Dashboard** - Monitors Stage B (parallel runners) CPU/memory, parallelism
   - Filter: `component=epymodelingsuite AND stage=runner`
   - Metrics: CPU %, Memory %, Memory MiB, CPU cores, Active instances

3. **Overall System Dashboard** - Monitors all stages combined
   - Filter: `component=epymodelingsuite`
   - Metrics: Aggregated CPU/memory by stage, Active instances by stage

**Access dashboards:**
```bash
# After terraform apply, get dashboard URLs:
cd terraform && terraform output | grep dashboard
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