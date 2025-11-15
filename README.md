# epymodelingsuite-cloud

Serverless, scalable pipeline for running epydemix simulations/calibration on Google Cloud using Cloud Batch + Workflows.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Glossary](#glossary)
  - [Core Concepts](#core-concepts)
  - [Pipeline Stages](#pipeline-stages)
  - [Google Cloud Batch Concepts](#google-cloud-batch-concepts)
  - [Execution Modes](#execution-modes)
- [Key Files & Documentation](#key-files--documentation)
- [Configuration](#configuration)

## Overview

This pipeline orchestrates two-stage job runs on Google Cloud with [Workflows](https://cloud.google.com/workflows):

**Pipeline Flow:**
- **Stage A (Dispatcher/Builder)** - Single task that generates N input configuration files → GCS
- **Stage B (Runner)** - N parallel tasks, each processing one input file → results to GCS
- **Stage C (Output)** - Single task that aggregates all results and generates formatted CSV outputs → GCS
- **Orchestration** - Cloud Workflows coordinates stage transitions with automatic retry logic


## Quick Start

**Initial Setup:**
- See [docs/google-cloud-guide.md](docs/google-cloud-guide.md#quick-start) for complete setup instructions
- Covers: environment configuration, GitHub PAT setup, infrastructure deployment, and first run

**Routine Operations:**
- See [docs/operations.md](docs/operations.md) for running workflows, monitoring, and troubleshooting
- Quick commands for building, deploying, and running experiments


## Glossary

Understanding the key concepts and terminology used throughout this pipeline:

<details>
<summary><h3>Core Concepts</h3></summary>

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

</details>

<details>
<summary><h3>Pipeline Stages</h3></summary>

**Stage A (Builder)**
- Generates N input configuration files (pickled Python objects)
- Runs as a single Google Cloud Batch job with 1 task
- Outputs: `{EXP_ID}/{RUN_ID}/builder-artifacts/input_0000.pkl` through `input_{N-1}.pkl`
- Script: [docker/scripts/main_builder.py](docker/scripts/main_builder.py)

**Builder**
- Another name for Stage A
- The component that "builds" or generates input configurations
- Labeled with `stage: builder` in Google Cloud resources

**Stage B (Runner)**
- Processes N simulations in parallel
- Runs as a single Google Cloud Batch job with N tasks
- Each task processes one input file (determined by `BATCH_TASK_INDEX`)
- Outputs: `{EXP_ID}/{RUN_ID}/runner-artifacts/result_0000.pkl` through `result_{N-1}.pkl`
- Script: [docker/scripts/main_runner.py](docker/scripts/main_runner.py)

**Runner**
- Another name for Stage B or individual simulation tasks
- The component that "runs" the actual simulations
- Labeled with `stage: runner` in Google Cloud resources

**Simulation**
- A single execution of the epydemix model with specific parameters
- Synonymous with "task" in this pipeline context
- Each simulation processes one input configuration file and produces one result file
- Example: Running 100 simulations = Stage B job with 100 tasks

**Stage C (Output)**
- Aggregates all Stage B results and generates formatted outputs
- Runs as a single Google Cloud Batch job with 1 task
- Reads all result files from Stage B and produces CSV.gz files
- Outputs: `{EXP_ID}/{RUN_ID}/outputs/*.csv.gz` (quantiles, trajectories, metadata, etc.)
- Script: [docker/scripts/main_output.py](docker/scripts/main_output.py)

**Output**
- Another name for Stage C
- The component that "outputs" formatted results for downstream analysis
- Labeled with `stage: output` in Google Cloud resources

</details>

<details>
<summary><h3>Google Cloud Batch Concepts</h3></summary>

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

</details>

<details>
<summary><h3>Execution Modes</h3></summary>

**Cloud Execution**
- Runs on Google Cloud Batch
- Uses GCS for storage
- Environment: `EXECUTION_MODE=cloud`
- Commands: `epycloud run workflow`, `epycloud workflow list`

**Local Execution**
- Runs via Docker Compose on your machine
- Uses local filesystem (`./local/bucket/`)
- Environment: `EXECUTION_MODE=local`
- Commands: `epycloud run local builder`, `epycloud run local runner`

</details>


## Key Files & Documentation

**Documentation:**
- **[/docs/google-cloud-guide.md](/docs/google-cloud-guide.md)** - Setup and detailed implementation guide
- **[/docs/operations.md](/docs/operations.md)** - Operational commands and common workflows
- **[/docs/variable-configuration.md](/docs/variable-configuration.md)** - Environment variable reference

**Infrastructure:**
- **[terraform/](terraform/)** - Infrastructure as code
  - [main.tf](terraform/main.tf) - Google Cloud resources
  - [workflow.yaml](terraform/workflow.yaml) - Orchestration logic

**CLI Tool:**
- **[src/epycloud/](src/epycloud/)** - Python CLI for managing pipeline
  - Configuration management
  - Workflow execution and monitoring
  - Build and deployment commands
  - Terraform wrapper

**Application:**
- **[docker/scripts/](docker/scripts/)** - Docker runtime scripts
  - [main_builder.py](docker/scripts/main_builder.py) - Stage A generator
  - [main_runner.py](docker/scripts/main_runner.py) - Stage B runner
  - [main_output.py](docker/scripts/main_output.py) - Stage C output generator
  - [run_builder.sh](docker/scripts/run_builder.sh) - Stage A wrapper for repo cloning
  - [run_output.sh](docker/scripts/run_output.sh) - Stage C wrapper
- **[docker/](docker/)** - Container config
  - [Dockerfile](docker/Dockerfile) - Multi-stage build (local and cloud targets)
- **[docker-compose.yml](docker-compose.yml)** - Local development setup


## Configuration

Configuration is managed through environment variables and templates:

**Files:**
- [.env.example](.env.example) - Project configuration template (copy to `.env`)
- [.env.local.example](.env.local.example) - Local secrets template (copy to `.env.local`)
- [/docs/variable-configuration.md](/docs/variable-configuration.md) - Complete variable reference

**Key variables:**
- `PROJECT_ID`, `REGION`, `BUCKET_NAME` - Google Cloud infrastructure
- `EXP_ID` - Experiment identifier (required for runs)
- `GITHUB_FORECAST_REPO`, `GITHUB_MODELING_SUITE_REPO` - Private repository access
- `STAGE_B_CPU_MILLI`, `STAGE_B_MEMORY_MIB`, `STAGE_B_MACHINE_TYPE` - Compute resources

`.env.local` is gitignored for security.