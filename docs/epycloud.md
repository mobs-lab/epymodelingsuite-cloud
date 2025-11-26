# epycloud

`epycloud` is a command-line tool for managing serverless, scalable pipelines for running `epydemix` simulations and calibrations on Google Cloud. It provides a professional interface for:
- **Building** Docker images for pipeline execution
- **Running** workflows and individual pipeline stages
- **Monitoring** execution status and viewing logs
- **Managing** infrastructure with Terraform
- **Validating** experiment configurations
- **Configuring** multi-environment deployments


## Table of Contents
1. [Quick Start](#quick-start)
2. [Installation](#installation)
3. [Core Concepts](#core-concepts)
4. [Configuration](#configuration)
5. [Command Reference](#command-reference)


## Quick Start

### Initial setup

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to repository
# git clone https://github.com/mobs-lab/epymodelingsuite-cloud
cd epymodelingsuite-cloud

# Install epycloud as isolated CLI tool
uv tool install .

# Verify installation
epycloud --version

# Option 1: Use init command
# Initialize configuration
epycloud config init

# Edit configuration
epycloud config edit

# Option 2: Copy config files to ~/.config/epymodelingsuite-cloud/
mkdir -p ~/.config/epymodelingsuite-cloud/{environments,profiles}
cp config.yaml ~/.config/epymodelingsuite-cloud/
cp env_default.yaml ~/.config/epymodelingsuite-cloud/environments/
cp profile_flu.yaml ~/.config/epymodelingsuite-cloud/profiles/

# Add your GitHub Personal Access Token
epycloud config edit-secrets

# You're ready!
epycloud --help
```

### First Run

```bash
# Build Docker image
epycloud build dev

# Run workflow locally for testing
epycloud run workflow --exp-id test-sim --local

# Or submit to cloud (dev environment)
epycloud run workflow --exp-id my-experiment

# Monitor progress
epycloud status --watch

# View logs
epycloud logs --exp-id my-experiment --follow
```


## Installation

### Recommended: Install with uv (Isolated Tool)

This installs `epycloud` as a globally available command without affecting your system Python:

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install epycloud from source
# git clone https://github.com/mobs-lab/epymodelingsuite-cloud
cd epymodelingsuite-cloud
uv tool install .

# Update after pulling code changes
uv tool upgrade epycloud

# Use directly (no environment activation needed)
epycloud --help
epycloud config show
```

The tool is installed in `~/.local/bin/epycloud`.

### Development Mode

For development and contributing to epycloud:

```bash
# git clone https://github.com/mobs-lab/epymodelingsuite-cloud
cd epymodelingsuite-cloud

# Install dependencies in development mode
uv sync

# Run CLI commands (automatically picks up local code changes)
uv run epycloud --help
uv run epycloud config show
```

**From PyPI (future):**
```bash
uv tool install epycloud
```

**From Git (future):**
```bash
uv tool install git+https://github.com/mobs-lab/epymodelingsuite-cloud.git
```

### Configuration Setup

After installation, initialize the configuration system:

```bash
# Option 1: Use init command
# Initialize configuration
epycloud config init

# Edit configuration
epycloud config edit

# Option 2: Copy config files to ~/.config/epymodelingsuite-cloud/
mkdir -p ~/.config/epymodelingsuite-cloud/{environments,profiles}
cp config.yaml ~/.config/epymodelingsuite-cloud/
cp env_default.yaml ~/.config/epymodelingsuite-cloud/environments/
cp profile_flu.yaml ~/.config/epymodelingsuite-cloud/profiles/

# Add secrets (GitHub PAT, etc.)
epycloud config edit-secrets
```

All epycloud commands and local Docker operations now use this unified configuration system.


## Core Concepts

See [README.md](../README.md#glossary) for core concepts like Experiment (EXP_ID), Run (RUN_ID), Workflow Execution, and Pipeline Stages.

### Environment vs Profile

**Environment (dev/prod/local)** - Infrastructure target:
- CLI flag: `epycloud --env=prod`
- **Explicit** - always visible in commands
- **Stateless** - no hidden state
- Controls: Resources, GCP project, deployment target

**Profile (flu/covid/rsv)** - Project configuration:
- Activation: `epycloud profile use flu`
- **Stateful** - persists between commands
- **Convenient** - don't repeat on every command
- Controls: Forecast repo, default settings, project-specific resources

### Execution Modes

epycloud supports execution of simulation/calibration both in cloud and locally.

**Cloud Execution:**
- Runs on Google Cloud Batch
- Uses GCS for storage
- Command: `epycloud run workflow --exp-id test`

**Local Execution:**
- Runs via Docker Compose on your machine
- Uses local filesystem (`./local/bucket/`)
- Command: `epycloud run workflow --exp-id test --local`


## Configuration

### XDG Directory Structure

```
~/.config/epymodelingsuite-cloud/     # XDG_CONFIG_HOME
├── config.yaml                        # Base configuration
├── secrets.yaml                       # Secrets (gitignored)
├── active_profile                     # Current profile: "flu"
├── environments/                      # Infrastructure environments
│   ├── dev.yaml                      # Development overrides
│   ├── prod.yaml                     # Production overrides
│   └── local.yaml                    # Local development
└── profiles/                          # Project/disease profiles
    ├── flu.yaml                       # Flu forecasting
    ├── covid.yaml                     # COVID modeling
    └── rsv.yaml                       # RSV modeling

~/.local/share/epymodelingsuite-cloud/ # XDG_DATA_HOME
└── cache/

~/.cache/epymodelingsuite-cloud/       # XDG_CACHE_HOME
└── build-cache/
```

### Configuration Hierarchy

Configuration is merged in order from lowest to highest priority:

1. **Base config** - `~/.config/epymodelingsuite-cloud/config.yaml`
2. **Environment config** - `environments/{env}.yaml` (dev/prod/local)
3. **Profile config** - `profiles/{profile}.yaml` (flu/covid/rsv)
4. **Project config** - `./epycloud.yaml` (optional, in current directory)
5. **Environment variables** - `EPYCLOUD_*`
6. **Command-line arguments** - `--project-id`, etc.

### Example Configuration

**Base config** (`~/.config/epymodelingsuite-cloud/config.yaml`):
```yaml
default:
  google_cloud:
    project_id: my-project
    region: us-central1
    bucket_name: my-bucket

  github:
    forecast_repo: mobs-lab/flu-forecast-epydemix
```

**Environment config** (`environments/prod.yaml`):
```yaml
# Production overrides
pipeline:
  max_parallelism: 100

resources:
  stage_b:
    cpu_milli: 4000
    memory_mib: 16384
```

**Secrets** (`secrets.yaml`):
```yaml
github:
  personal_access_token: github_pat_xxxxxxxxxxxxxxxxxxxxx
```

### Environment Variables

Override config with environment variables (optional):

```bash
# Environment selection
export EPYCLOUD_ENV=prod

# Config overrides
export EPYCLOUD_PROJECT_ID=my-project
export EPYCLOUD_REGION=us-west1
export EPYCLOUD_BUCKET=my-bucket

# GitHub token (for validate command)
export GITHUB_TOKEN=github_pat_xxxxx

# Secrets
export EPYCLOUD_GITHUB_PAT=github_pat_xxxxx
```

### Docker Build with Private Repositories

Docker builds that include private repositories (e.g., modeling suite) require a GitHub Personal Access Token. This should be configured in `secrets.yaml`:

```bash
# Add your GitHub PAT to secrets
epycloud config edit-secrets

# Add the following to secrets.yaml:
# github:
#   personal_access_token: github_pat_xxxxx

# Now you can build
epycloud build dev
```

The build commands automatically read the GitHub PAT from `secrets.yaml` and pass it to Docker as a build argument.


## Command Reference

### Global Options

```bash
epycloud [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]

Global Options:
  -h, --help              Show help
  -v, --version           Show version
  -e, --env ENV           Environment: dev|prod|local (default: dev)
  --profile PROFILE       Override active profile
  -c, --config PATH       Config file path
  -d, --project-dir PATH  Project directory
  --verbose               Verbose output
  --quiet                 Quiet mode
  --dry-run               Show what would happen
```

### 1. run - Execute Pipeline

Execute complete workflows or individual pipeline stages. Workflows orchestrate all three stages (Builder → Runner → Output) automatically, while individual jobs allow running specific stages for debugging or testing.

#### run workflow

Submit a complete workflow that runs all three stages sequentially.

```bash
epycloud run workflow --exp-id EXP_ID [OPTIONS]

Options:
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (auto-generated if not provided)
  --local               Run locally with docker compose
  --skip-output         Skip stage C (output generation)
  --max-parallelism N   Max parallel tasks
  --wait                Wait for completion and stream logs
  --output-config FILE  Output config filename for Stage C (e.g., output2.yaml)

Examples:
  # Submit workflow to cloud (dev environment)
  epycloud run workflow --exp-id flu-2024

  # Submit to production
  epycloud --env=prod run workflow --exp-id real-study

  # Run entire workflow locally
  epycloud run workflow --exp-id test-sim --local

  # Submit and wait for completion
  epycloud run workflow --exp-id flu-2024 --wait

  # Use specific output config for Stage C
  epycloud run workflow --exp-id flu-2024 --output-config output2.yaml
```

#### run job

Run a single stage or individual task. Useful for debugging specific stages or running tasks locally during development.

```bash
epycloud run job --stage STAGE --exp-id EXP_ID [OPTIONS]

Stages:
  A, builder            Stage A: Builder (generate input files)
  B, runner             Stage B: Runner (parallel tasks)
  C, output             Stage C: Output (aggregate results)

Options:
  --stage STAGE         Stage to run (required)
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (required for stages B and C)
  --task-index N        Task index for stage B (default: 0)
  --num-tasks N         Number of tasks (required for stage C)
  --local               Run locally with docker compose
  --wait                Wait for completion and stream logs
  --output-config FILE  Output config filename for Stage C (e.g., output2.yaml)

Examples:
  # Run builder stage locally
  epycloud run job --stage builder --exp-id test-sim --local

  # Run specific task (stage B, task 5)
  epycloud run job --stage B --exp-id flu --run-id 20251106-123456 --task-index 5

  # Run output generation (stage C)
  epycloud run job --stage C --exp-id flu --run-id 20251106-123456 --num-tasks 100

  # Run output with specific config (allows re-running with different output settings)
  epycloud run job --stage C --exp-id flu --run-id 20251106-123456 --num-tasks 100 --output-config output2.yaml
```

### 2. build - Build Docker Images

Build Docker images for the pipeline. Cloud builds use Google Cloud Build service (asynchronous), local builds use your Docker daemon and push to Artifact Registry, and dev builds create local-only images for testing.

```bash
epycloud build [MODE] [OPTIONS]

Modes:
  cloud                 Build with Cloud Build (default, async)
  local                 Build locally and push to registry
  dev                   Build dev image locally (no push)

Options:
  --no-cache            Disable build cache
  --tag TAG             Image tag
  --push                Push to registry (for dev builds)
  --wait                Wait for build to complete (cloud builds)

Examples:
  # Build with Cloud Build (async)
  epycloud build
  epycloud build cloud

  # Build locally and push
  epycloud build local

  # Build dev image (no push)
  epycloud build dev

  # Build and wait for completion
  epycloud build cloud --wait
```

### 3. validate - Validate Configuration

Validate experiment configuration files before running workflows. Fetches YAML configs from GitHub or reads from local path, then validates using epymodelingsuite loaders to catch configuration errors early.

```bash
epycloud validate --exp-id EXP_ID [OPTIONS]
epycloud validate --path PATH [OPTIONS]

Options:
  --exp-id ID           Experiment ID from GitHub
  --path PATH           Local config directory path
  --format FORMAT       Output format: text|json|yaml
  --github-token TOKEN  GitHub PAT for remote validation

Examples:
  # Validate experiment from GitHub
  epycloud validate --exp-id flu-2024

  # Validate local config directory
  epycloud validate --path ./local/forecast/experiments/test-sim/config

  # Output as JSON for CI/CD
  epycloud validate --exp-id prod-study --format json

Exit Codes:
  0    Validation passed
  1    Validation failed
  2    Configuration error
```

### 4. config - Configuration Management

Manage epycloud configuration files, view merged settings, and edit configs. Supports initialization, validation, and access to both base and environment-specific configurations.

```bash
epycloud config SUBCOMMAND [OPTIONS]

Subcommands:
  init                  Initialize config directory
  show                  Show current configuration
  edit                  Edit config in $EDITOR
  validate              Validate configuration
  path                  Show config directory path
  get KEY               Get specific config value
  set KEY VALUE         Set config value

Examples:
  # Initialize config (first-time setup)
  epycloud config init

  # Show full merged configuration
  epycloud config show

  # Show config for production
  epycloud --env=prod config show

  # Get specific value
  epycloud config get google_cloud.project_id

  # Edit base config
  epycloud config edit

  # Show config directory
  epycloud config path
```

### 5. workflow - Workflow Management

Manage Google Cloud Workflows executions. List, describe, monitor, and control workflow runs. View execution details, stream logs, and cancel running workflows.

```bash
epycloud workflow SUBCOMMAND [OPTIONS]

Subcommands:
  list                  List workflow executions
  describe              Describe execution details
  logs                  Stream execution logs
  cancel                Cancel running execution

Options:
  --limit N             Number of executions to show (default: 10)
  --status STATUS       Filter by status
  --exp-id ID           Filter by experiment ID
  --since DURATION      Show executions since (e.g., 24h, 7d)

Examples:
  # List recent executions
  epycloud workflow list

  # Filter by experiment
  epycloud workflow list --exp-id flu-2024

  # Describe specific execution
  epycloud workflow describe abc123

  # Stream logs (follow mode)
  epycloud workflow logs abc123 --follow

  # Cancel running execution
  epycloud workflow cancel abc123
```

### 6. status - Monitor Pipeline

Monitor active workflows and Cloud Batch jobs in real-time. Shows current execution status, running jobs, task progress, and supports watch mode for continuous monitoring.

```bash
epycloud status [OPTIONS]

Options:
  --exp-id ID           Filter by experiment ID
  --watch               Watch mode (auto-refresh)
  --interval N          Refresh interval in seconds (default: 10)

Examples:
  # Show status of all active pipelines
  epycloud status

  # Filter by experiment
  epycloud status --exp-id flu-2024

  # Watch mode with auto-refresh
  epycloud status --watch

  # Watch with custom interval
  epycloud status --exp-id flu-2024 --watch --interval 5
```

### 7. logs - View Logs

View and stream logs from Cloud Batch jobs via Cloud Logging API. Filter by experiment, run, stage, task, severity level, or time range. Supports real-time log streaming with follow mode.

```bash
epycloud logs --exp-id EXP_ID [OPTIONS]

Options:
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (optional)
  --stage STAGE         Stage: A|B|C|builder|runner|output
  --task-index N        Task index for stage B
  --follow, -f          Follow mode (stream logs)
  --tail N              Show last N lines (default: 100)
  --since DURATION      Show logs since (e.g., 1h, 30m)
  --level LEVEL         Filter by log level

Examples:
  # View logs for experiment
  epycloud logs --exp-id flu-2024

  # View stage B logs
  epycloud logs --exp-id flu-2024 --stage B

  # Follow logs in real-time
  epycloud logs --exp-id flu-2024 --follow

  # Show last 500 lines
  epycloud logs --exp-id flu-2024 --tail 500

  # Show errors only
  epycloud logs --exp-id flu-2024 --level ERROR
```

### 8. profile - Profile Management

Manage disease/project-specific configuration profiles. Create, activate, edit, and switch between profiles (flu/covid/rsv). Profiles persist settings like forecast repository, default resources, and project-specific configurations.

```bash
epycloud profile SUBCOMMAND [OPTIONS]

Subcommands:
  list                  List all profiles
  use PROFILE           Activate a profile
  current               Show active profile
  create NAME           Create new profile
  edit PROFILE          Edit profile config
  show PROFILE          Show profile details
  delete PROFILE        Delete profile

Examples:
  # List available profiles
  epycloud profile list

  # Activate a profile
  epycloud profile use covid

  # Show current profile
  epycloud profile current

  # Create new profile
  epycloud profile create mpox

  # Edit profile
  epycloud profile edit flu
```

### 9. terraform (alias: tf) - Infrastructure Management

Manage Google Cloud infrastructure with Terraform. Initialize, plan, apply, and destroy infrastructure resources. Supports environment-specific deployments (dev/prod) and targeted resource updates.

```bash
epycloud terraform SUBCOMMAND [OPTIONS]
epycloud tf SUBCOMMAND [OPTIONS]

Subcommands:
  init                  Initialize Terraform
  plan                  Plan infrastructure changes
  apply                 Apply changes
  destroy               Destroy infrastructure
  output [NAME]         Show Terraform outputs

Options:
  --auto-approve        Skip confirmation
  --target RESOURCE     Target specific resource

Examples:
  # Initialize
  epycloud tf init

  # Plan changes
  epycloud tf plan

  # Apply changes
  epycloud tf apply

  # Apply to production
  epycloud --env=prod tf apply

  # Destroy infrastructure
  epycloud tf destroy
```

## Further Documentation

For detailed operational workflows, see [operations.md](operations.md).

For complete setup and configuration guides:
- **[google-cloud-guide.md](google-cloud-guide.md)** - Complete setup and implementation guide
- **[operations.md](operations.md)** - Detailed operational commands and workflows
- **[variable-configuration.md](variable-configuration.md)** - Complete variable reference
- **[configuration-guide.md](configuration-guide.md)** - Configuration system details
- **[design-and-architecture.md](design-and-architecture.md)** - Design decisions and architecture
- **[command-reference.md](command-reference.md)** - Complete command reference

