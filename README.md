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

After running `make tf-apply`, four Cloud Monitoring dashboards are automatically created:

1. **Image Build Dashboard** - Monitors Cloud Build execution time and status
   - Filter: `component=epymodelingsuite AND stage=imagebuild`

2. **Builder Dashboard** - Monitors Stage A (dispatcher) CPU/memory usage
   - Filter: `component=epymodelingsuite AND stage=builder`

3. **Runner Dashboard** - Monitors Stage B (parallel runners) CPU/memory, parallelism
   - Filter: `component=epymodelingsuite AND stage=runner`

4. **Overall System Dashboard** - Monitors all stages combined
   - Filter: `component=epymodelingsuite`

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