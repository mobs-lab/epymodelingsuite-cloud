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
source .env

# 2. Deploy infrastructure
make tf-init && make tf-apply

# 3. Build Docker image
make build

# 4. Run pipeline
make run-workflow

# Or customize:
RUN_COUNT=50 SIM_ID=experiment-01 make run-workflow
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
- **[Makefile](Makefile)** - Build/deploy automation
- **[/docs/variable-configuration.md](/docs/variable-configuration.md)** - Environment variable reference

## Configuration

See [.env](.env), [.env.example](.env.example), and [/docs/variable-configuration.md](/docs/variable-configuration.md) for required environment variables.