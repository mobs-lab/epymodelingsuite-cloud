# epycloud Command Reference

**Version:** 1.0
**Created:** 2025-11-06

A refined, intuitive command structure for the `epycloud` CLI tool.

---

## Design Principles

1. **Simple and intuitive** - Commands match mental model
2. **Consistent flags** - Same flags work across commands
3. **Smart defaults** - Cloud mode by default, `--local` to override
4. **Discoverable** - Clear help text and examples
5. **Safe** - Verification before expensive operations

---

## Command Structure

```
epycloud [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]
```

### Global Options

```bash
-h, --help              Show help
-v, --version           Show version
-e, --env ENV           Environment: dev|prod|local (default: dev)
-c, --config PATH       Config file path (default: ~/.config/epymodelingsuite-cloud/config.yaml)
-d, --project-dir PATH  Project directory (default: current directory)
--verbose               Verbose output
--quiet                 Quiet mode (errors only)
--dry-run               Show what would happen without executing
```

---

## Commands

### 1. run - Execute Pipeline Stages

Run pipeline workflows or individual stages.

#### run workflow

Submit a complete workflow (all stages: A → B → C).

```bash
epycloud run workflow --exp-id EXP_ID [OPTIONS]

Options:
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (auto-generated if not provided)
  --local               Run locally with docker compose instead of cloud
  --skip-output         Skip stage C (output generation)
  --max-parallelism N   Max parallel tasks (default: from config)
  --wait                Wait for completion and stream logs

Examples:
  # Submit workflow to cloud (dev environment)
  epycloud run workflow --exp-id flu-2024

  # Submit to production
  epycloud --env=prod run workflow --exp-id real-study

  # Run entire workflow locally
  epycloud run workflow --exp-id test-sim --local

  # Submit and wait for completion
  epycloud run workflow --exp-id flu-2024 --wait

  # Skip output generation (stages A and B only)
  epycloud run workflow --exp-id test --skip-output
```

#### run job

Run a single stage or task.

```bash
epycloud run job --stage STAGE --exp-id EXP_ID [OPTIONS]

Stages:
  A, builder            Stage A: Builder (generate input files)
  B, runner             Stage B: Runner (parallel tasks)
  C, output             Stage C: Output (aggregate results)

Options:
  --stage STAGE         Stage to run: A|B|C|builder|runner|output (required)
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (required for stages B and C, auto-generated for stage A)
  --task-index N        Task index for stage B (default: 0)
  --num-tasks N         Number of tasks (required for stage C)
  --local               Run locally with docker compose instead of cloud
  --wait                Wait for completion and stream logs

Examples:
  # Run builder stage on cloud
  epycloud run job --stage A --exp-id flu-2024

  # Run builder locally
  epycloud run job --stage builder --exp-id test-sim --local

  # Run specific task (stage B, task 5)
  epycloud run job --stage B --exp-id flu --run-id 20251106-123456 --task-index 5

  # Run output generation (stage C)
  epycloud run job --stage C --exp-id flu --run-id 20251106-123456 --num-tasks 100

  # Run single task locally for debugging
  epycloud run job --stage runner --exp-id test --run-id debug-001 --task-index 0 --local
```

### 2. build - Build Docker Images

Build and push Docker images for the pipeline.

```bash
epycloud build [MODE] [OPTIONS]

Modes:
  cloud                 Build with Cloud Build (default, async)
  local                 Build locally and push to registry
  dev                   Build dev image locally (no push)

Options:
  --no-cache            Disable build cache
  --tag TAG             Image tag (default: from config)
  --push                Push to registry (for local/dev builds)
  --no-push             Don't push to registry
  --wait                Wait for build to complete (cloud builds)

Examples:
  # Build with Cloud Build (default, async)
  epycloud build
  epycloud build cloud

  # Build locally and push
  epycloud build local

  # Build dev image (no push)
  epycloud build dev

  # Build without cache
  epycloud build --no-cache

  # Build and wait for completion
  epycloud build cloud --wait

  # Build dev image and push for testing
  epycloud build dev --push
```

### 3. validate - Validate Experiment Configuration

Validate experiment configuration using epymodelingsuite. Can validate from GitHub repository or local path.

```bash
epycloud validate --exp-id EXP_ID [OPTIONS]
epycloud validate --path PATH [OPTIONS]

Options:
  --exp-id ID           Experiment ID to validate from GitHub (mutually exclusive with --path)
  --path PATH           Path to local config directory (mutually exclusive with --exp-id)
  --format FORMAT       Output format: text|json|yaml (default: text)
  --github-token TOKEN  GitHub PAT for remote validation (or use from config/secrets/env)

Validation Process:
  1. Fetch or read YAML config files
  2. Classify configs by type (basemodel, sampling, calibration, output)
  3. Load configs using epymodelingsuite loaders
  4. Validate cross-config consistency
  5. Report pass/fail for the config set

Examples:
  # Validate experiment from GitHub (remote)
  epycloud validate --exp-id flu-2024

  # Validate local config directory
  epycloud validate --path ./local/forecast/experiments/test-sim/config

  # Output as JSON for CI/CD
  epycloud validate --exp-id prod-study --format json

  # Output as YAML
  epycloud validate --path ./config --format yaml

Output (Text):
  Validating: mobs-lab/flu-forecast-epydemix/experiments/flu-2024/config

  ✓ Validation passed: basemodel_config.yaml + sampling_config.yaml

Output (JSON):
  {
    "directory": "mobs-lab/flu-forecast-epydemix/experiments/flu-2024/config",
    "config_sets": [
      {
        "basemodel": "basemodel_config.yaml",
        "modelset": "sampling_config.yaml",
        "status": "pass"
      }
    ]
  }

Exit Codes:
  0    Validation passed
  1    Validation failed (errors found)
  2    Configuration error (missing token, repo, etc.)
```

### 4. config - Configuration Management

Manage epycloud configuration.

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

  # Show raw YAML
  epycloud config show --raw

  # Show config for specific environment
  epycloud --env=prod config show

  # Get specific value
  epycloud config get google_cloud.project_id

  # Set value
  epycloud config set google_cloud.region us-west1

  # Edit base config in editor
  epycloud config edit

  # Edit environment config
  epycloud config edit --env prod

  # Validate config syntax
  epycloud config validate

  # Show config directory
  epycloud config path
  # Output: /home/user/.config/epymodelingsuite-cloud
```

### 5. workflow - Workflow Management

Manage Cloud Workflows executions.

```bash
epycloud workflow SUBCOMMAND [OPTIONS]

Subcommands:
  list                  List workflow executions
  describe              Describe execution details
  logs                  Stream execution logs
  cancel                Cancel running execution
  retry                 Retry failed execution

List Options:
  --limit N             Number of executions to show (default: 10)
  --status STATUS       Filter by status: ACTIVE|SUCCEEDED|FAILED|CANCELLED
  --exp-id ID           Filter by experiment ID
  --since DURATION      Show executions since (e.g., 24h, 7d, 30m)

Logs Options:
  --follow, -f          Follow log output (stream mode)
  --tail N              Show last N lines (default: 100)

Examples:
  # List recent executions
  epycloud workflow list

  # List last 20 executions
  epycloud workflow list --limit 20

  # Filter by status
  epycloud workflow list --status FAILED

  # Filter by experiment
  epycloud workflow list --exp-id flu-2024

  # Show executions from last 24 hours
  epycloud workflow list --since 24h

  # Describe specific execution (supports short ID or full name)
  epycloud workflow describe abc123
  epycloud workflow describe projects/123/locations/us-central1/workflows/pipeline/executions/abc

  # Stream logs (follow mode)
  epycloud workflow logs abc123 --follow

  # Show last 500 lines of logs
  epycloud workflow logs abc123 --tail 500

  # Cancel running execution
  epycloud workflow cancel abc123

  # Retry failed execution
  epycloud workflow retry abc123
```

### 6. status - Check Pipeline Status

Monitor active workflows and Cloud Batch jobs with real-time status updates.

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

  # Watch specific experiment with custom interval
  epycloud status --exp-id flu-2024 --watch --interval 5

Output:
  Pipeline Status
  ====================================================================================================

  Active Workflows:

  EXECUTION ID                             EXP_ID               START TIME
  ----------------------------------------------------------------------------------------------------
  a1b2c3d4-e5f6-7890-abcd-ef1234567890    flu-2024             2025-11-07 14:30:52

  Active Batch Jobs:

  JOB NAME                                          STAGE    STATUS       TASKS
  ----------------------------------------------------------------------------------------------------
  epymodelingsuite-flu-2024-20251107-143052-B      B        RUNNING      45/100

  Total active: 1 workflow(s), 1 batch job(s)

Watch Mode:
  - Auto-refreshes every N seconds (default: 10)
  - Clears screen between updates
  - Shows last update timestamp
  - Press Ctrl+C to stop watching
```

### 7. logs - View Logs

View logs from Cloud Batch jobs via Cloud Logging API.

```bash
epycloud logs --exp-id EXP_ID [OPTIONS]

Options:
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (optional, shows all runs if not specified)
  --stage STAGE         Stage: A|B|C|builder|runner|output
  --task-index N        Task index for stage B (default: all tasks)
  --follow, -f          Follow mode (stream logs)
  --tail N              Show last N lines (default: 100)
  --since DURATION      Show logs since (e.g., 1h, 30m, 24h)
  --level LEVEL         Filter by log level: DEBUG|INFO|WARNING|ERROR

Examples:
  # View logs for experiment (all runs)
  epycloud logs --exp-id flu-2024

  # View logs for specific run
  epycloud logs --exp-id flu-2024 --run-id 20251107-143052

  # View stage B logs
  epycloud logs --exp-id flu-2024 --stage B

  # View specific task logs
  epycloud logs --exp-id flu-2024 --stage B --task-index 5

  # Follow logs in real-time
  epycloud logs --exp-id flu-2024 --follow

  # Show last 500 lines
  epycloud logs --exp-id flu-2024 --tail 500

  # Show errors only
  epycloud logs --exp-id flu-2024 --level ERROR

  # Show recent logs
  epycloud logs --exp-id flu-2024 --since 1h

Output:
  [2025-11-07 14:30:52] INFO [stage=B, task=5]
    Starting task execution...

  [2025-11-07 14:30:55] INFO [stage=B, task=5]
    Loading input file: builder-artifacts/input_0005.pkl

  [2025-11-07 14:31:00] ERROR [stage=B, task=5]
    Validation failed: missing required field

Follow Mode:
  - Polls for new logs every 5 seconds
  - Displays logs in chronological order
  - Color-coded severity (ERROR=red, WARNING=yellow, DEBUG=gray)
  - Press Ctrl+C to stop streaming
```

### 8. profile - Profile Management

Manage disease/project profiles.

```bash
epycloud profile SUBCOMMAND [OPTIONS]

Subcommands:
  list                  List all profiles
  use PROFILE           Activate a profile (like conda activate)
  current               Show active profile
  create NAME           Create new profile
  edit PROFILE          Edit profile config
  show PROFILE          Show profile details
  delete PROFILE        Delete profile

Options:
  --template TEMPLATE   Template for new profile: basic|full

Examples:
  # List available profiles
  epycloud profile list
  # Output:
  # Available profiles:
  #   flu     - Influenza forecasting models
  #   covid   - COVID-19 modeling
  #   rsv     - RSV modeling
  #
  # Active: flu (*)

  # Show current active profile
  epycloud profile current
  # Output: flu

  # Activate a profile
  epycloud profile use covid

  # Create new profile
  epycloud profile create mpox

  # Create with template
  epycloud profile create mpox --template basic

  # Show profile details
  epycloud profile show flu

  # Edit profile
  epycloud profile edit flu

  # Delete profile
  epycloud profile delete old-project
```

### 9. terraform (alias: tf) - Infrastructure Management

Manage infrastructure with Terraform.

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
  --auto-approve        Skip confirmation (apply/destroy only)
  --target RESOURCE     Target specific resource

Examples:
  # Initialize
  epycloud tf init

  # Plan changes
  epycloud tf plan

  # Apply changes (dev environment)
  epycloud tf apply

  # Apply to production (with confirmation)
  epycloud --env=prod tf apply

  # Destroy dev infrastructure
  epycloud tf destroy

  # Show specific output
  epycloud tf output batch_runtime_sa_email
```

---

## Low Priority Commands (Phase 2)

These commands are planned for future releases but not in the MVP.

### download - Download Results

Download output files from GCS.

```bash
epycloud download [OPTIONS] [DESTINATION]

Options:
  --exp-id ID           Experiment ID (required)
  --run-id ID           Run ID (required)
  --output-type TYPE    Output type: all|trajectories|quantiles|metadata
  --destination PATH    Download destination (default: ./outputs)

Examples:
  # Download all outputs
  epycloud download --exp-id flu-2024 --run-id 20251106-123456

  # Download to specific directory
  epycloud download --exp-id flu-2024 --run-id 20251106-123456 ./results

  # Download only trajectories
  epycloud download --exp-id flu --run-id 20251106-123456 --output-type trajectories

  # Download and extract
  epycloud download --exp-id flu --run-id 20251106-123456 --extract
```

**Alternative:** Use `gsutil` or GCS console for now.

### list - List Resources

List experiments, runs, and outputs.

```bash
epycloud list RESOURCE [OPTIONS]

Resources:
  experiments           List all experiments
  runs                  List runs for an experiment
  outputs               List output files

Options:
  --exp-id ID           Filter by experiment ID
  --since DURATION      Show items since (e.g., 7d)
  --status STATUS       Filter by status
  --format FORMAT       Output format: text|json|csv

Examples:
  # List all experiments
  epycloud list experiments

  # List runs for experiment
  epycloud list runs --exp-id flu-2024

  # List recent runs
  epycloud list runs --since 7d

  # List output files
  epycloud list outputs --exp-id flu-2024 --run-id 20251106-123456

  # Export as CSV
  epycloud list runs --exp-id flu-2024 --format csv > runs.csv
```

**Alternative:** Use `epycloud workflow list` and `epycloud status` commands for now.

---

## Common Workflows

### 1. First-Time Setup

```bash
# Install epycloud (recommended: use uv tool install)
cd /path/to/epymodelingsuite-cloud
uv tool install .

# Or for development
uv sync

# Initialize config
epycloud config init

# Verify installation
epycloud --version
epycloud config show
```

### 2. Run a New Experiment

```bash
# Validate config first
epycloud validate --exp-id flu-2024

# Build image if needed
epycloud build

# Submit workflow
epycloud run workflow --exp-id flu-2024

# Monitor progress
epycloud status --exp-id flu-2024 --watch

# View logs
epycloud logs --exp-id flu-2024 --follow

# Download results when complete
epycloud download --exp-id flu-2024 --run-id <run-id>
```

### 3. Debug Failed Run

```bash
# Check status
epycloud status --exp-id test-sim

# View error logs
epycloud logs --exp-id test-sim --level ERROR

# Re-run single task locally
epycloud run job --stage B --exp-id test-sim --run-id <run-id> --task-index 5 --local

# Fix issue and retry
epycloud workflow retry <execution-id>
```

### 4. Production Deployment

```bash
# Switch to production
export EPYCLOUD_ENV=prod

# Validate config
epycloud validate --exp-id real-study

# Build production image
epycloud build

# Apply infrastructure
epycloud tf apply

# Submit workflow
epycloud run workflow --exp-id real-study --wait

# Monitor
epycloud status --watch
```

### 5. Local Development

```bash
# Build dev image
epycloud build dev

# Run workflow locally
epycloud run workflow --exp-id test-sim --local

# Or run stages individually
epycloud run job --stage A --exp-id test-sim --local
epycloud run job --stage B --exp-id test-sim --run-id test-001 --task-index 0 --local
epycloud run job --stage C --exp-id test-sim --run-id test-001 --num-tasks 10 --local
```

---

## Environment Variables

Override config with environment variables:

```bash
# Environment selection
export EPYCLOUD_ENV=prod

# Config overrides
export EPYCLOUD_PROJECT_ID=my-project
export EPYCLOUD_REGION=us-west1
export EPYCLOUD_BUCKET=my-bucket

# GitHub token (for verify command)
export GITHUB_TOKEN=github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)

# Secrets
export EPYCLOUD_GITHUB_PAT=github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)
```

---

## Configuration Files

### Global Config: `~/.config/epymodelingsuite-cloud/config.yaml`

```yaml
default:
  google_cloud:
    project_id: my-project
    region: us-central1
    bucket_name: my-bucket

  github:
    forecast_repo: mobs-lab/flu-forecast-epydemix
    # PAT stored in secrets.yaml
```

### Environment Config: `~/.config/epymodelingsuite-cloud/environments/prod.yaml`

```yaml
# Production overrides
pipeline:
  max_parallelism: 100

resources:
  stage_b:
    cpu_milli: 4000
    memory_mib: 16384
```

### Secrets: `~/.config/epymodelingsuite-cloud/secrets.yaml`

```yaml
github:
  personal_access_token: github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)xxxxxxxxxxxxxxxx
```

### Project Config: `./epycloud.yaml` (optional)

```yaml
# Project-specific overrides
google_cloud:
  project_id: flu-forecasting-project
  bucket_name: flu-data-bucket

pipeline:
  dir_prefix: "pipeline/{environment}/flu-2024/"
```

---

## Exit Codes

```
0    Success
1    General error
2    Configuration error
3    Validation error
4    Authentication error
5    Resource not found
6    Permission denied
7    Network error
8    Timeout
130  Interrupted (Ctrl+C)
```

---

## Aliases and Shortcuts

```bash
# Build aliases
epycloud build          # Same as: epycloud build cloud

# Terraform aliases
epycloud tf             # Same as: epycloud terraform

# Stage aliases (for run job)
--stage A               # Same as: --stage builder
--stage B               # Same as: --stage runner
--stage C               # Same as: --stage output

# Environment shortcuts
-e dev                  # Same as: --env=dev
```

---

## Tab Completion (Future)

```bash
# Bash completion
complete -C epycloud epycloud

# Or install completion script
epycloud completion bash > /etc/bash_completion.d/epycloud

# Zsh completion
epycloud completion zsh > ~/.zsh/completion/_epycloud
```

---

## Version Information

```bash
epycloud --version
# Output:
# epycloud version 0.1.0
# Python 3.11.5
# Config: /home/user/.config/epymodelingsuite-cloud
```

---

## Help System

Every command has detailed help:

```bash
epycloud --help                      # Main help
epycloud run --help                  # Run command help
epycloud run workflow --help         # Workflow subcommand help
epycloud validate --help             # Validate command help
```

---

**Document version:** 1.0
**Last updated:** 2025-11-06
