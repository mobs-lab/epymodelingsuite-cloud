# epycloud Configuration Guide

**Version:** 1.0
**Created:** 2025-11-06

A comprehensive guide to configuring `epycloud` with environments and profiles.

---

## Table of Contents

1. [Overview](#overview)
2. [Configuration Structure](#configuration-structure)
3. [Environments vs Profiles](#environments-vs-profiles)
4. [Base Configuration](#base-configuration)
5. [Environment Overrides](#environment-overrides)
6. [Profile Configuration](#profile-configuration)
7. [Configuration Merging](#configuration-merging)
8. [Secrets Management](#secrets-management)
9. [Examples](#examples)

---

## Overview

### Two Orthogonal Concepts

`epycloud` manages configuration using two independent concepts:

1. **Environment** (dev/prod/local) - **WHERE** you're running
   - Infrastructure/deployment target
   - Resource allocation
   - GCP project selection
   - Explicit via `--env` flag

2. **Profile** (flu/covid/rsv) - **WHAT** you're modeling
   - Disease/project-specific settings
   - Forecast repository
   - Default configurations
   - Stateful via `epycloud profile use`

### Configuration Locations

```
~/.config/epymodelingsuite-cloud/     # Main config directory
├── config.yaml                        # Base configuration
├── secrets.yaml                       # Secrets (gitignored)
├── active_profile                     # Current profile (e.g., "flu")
├── environments/
│   ├── dev.yaml                      # Development overrides
│   ├── prod.yaml                     # Production overrides
│   └── local.yaml                    # Local development
└── profiles/
    ├── flu.yaml                       # Flu forecasting
    ├── covid.yaml                     # COVID modeling
    └── rsv.yaml                       # RSV modeling

./epycloud.yaml                        # Optional project-local overrides
```

---

## Configuration Structure

### Logical Organization

Configuration is organized into logical sections:

```yaml
# Storage configuration (universal - both local and cloud)
storage:
  dir_prefix: "pipeline/{environment}/{profile}"

# Google Cloud Platform configuration
google_cloud:
  project_id: my-project-id
  region: us-central1
  bucket_name: my-bucket-name

  # Cloud Batch configuration
  batch:
    max_parallelism: 100
    task_count_per_node: 1

    stage_a:
      cpu_milli: 2000
      memory_mib: 4096
      machine_type: ""
      max_run_duration: 3600

    stage_b:
      cpu_milli: 2000
      memory_mib: 8192
      machine_type: ""
      max_run_duration: 36000

    stage_c:
      cpu_milli: 2000
      memory_mib: 8192
      machine_type: ""
      max_run_duration: 7200
      run_output_stage: true

# Docker image configuration
docker:
  registry: "us-central1-docker.pkg.dev"
  repo_name: epymodelingsuite-repo
  image_name: epymodelingsuite
  image_tag: latest

# GitHub repositories
github:
  modeling_suite_repo: mobs-lab/epymodelingsuite
  modeling_suite_ref: main
  # forecast_repo is profile-specific

# Logging configuration
logging:
  level: INFO
  storage_verbose: true

# Workflow configuration
workflow:
  retry_policy:
    max_attempts: 3
    backoff_seconds: 60
  notification:
    enabled: false
    email: null
```

### Section Rationale

**`storage`** - Universal storage config:
- Used by both local filesystem and cloud (GCS)
- `dir_prefix` template with `{environment}` and `{profile}` placeholders
- Local: `./local/bucket/{dir_prefix}/{exp_id}/{run_id}/`
- Cloud: `gs://{bucket}/{dir_prefix}/{exp_id}/{run_id}/`

**`google_cloud`** - All GCP-specific settings:
- Top-level: `project_id`, `region`, `bucket_name`
- `batch` subsection: All Cloud Batch configuration
  - Execution settings: `max_parallelism`, `task_count_per_node`
  - Stage resources: `stage_a`, `stage_b`, `stage_c`

**`github`** - GitHub repository configuration:
- `modeling_suite_repo` - Base package (usually same across profiles)
- `forecast_repo` - Profile-specific (flu/covid/rsv have different repos)

**`docker`** - Docker image configuration:
- Registry location and image details
- Separate from GCP (could use other registries)

**`logging`** - Application logging:
- Log level and verbosity
- Application-level, not infrastructure-level

**`workflow`** - Cloud Workflows settings:
- Retry policies
- Notifications
- Orchestration configuration

---

## Environments vs Profiles

### Environment (Infrastructure Target)

**What it controls:** Infrastructure, resources, deployment target

**How to use:**
```bash
# Explicit via CLI argument (recommended)
epycloud --env=dev build
epycloud --env=prod run workflow --exp-id study

# Via environment variable
export EPYCLOUD_ENV=prod
epycloud build

# Default is 'dev' (safe default)
epycloud build  # Uses dev
```

**Three environments:**

| Environment | Purpose | Resources | Safety |
|-------------|---------|-----------|--------|
| **dev** | Development testing | Lower (cheaper) | Default, safe |
| **prod** | Production runs | Full (expensive) | Confirmation prompts |
| **local** | Local Docker testing | N/A | Filesystem only |

**Why explicit?**
- ✅ Safety - can't accidentally run in prod
- ✅ Visibility - clear what environment you're using
- ✅ Stateless - no hidden state to forget
- ✅ CI/CD friendly - easy to script

### Profile (Project Configuration)

**What it controls:** Disease/project-specific settings, forecast repo

**How to use:**
```bash
# List available profiles
epycloud profile list

# Activate a profile (like conda activate)
epycloud profile use flu

# Now commands use flu profile
epycloud run workflow --exp-id weekly-forecast

# Switch profile
epycloud profile use covid

# Show current profile
epycloud profile current

# Override active profile for one command
epycloud --profile covid run workflow --exp-id test
```

**Why stateful activation?**
- ✅ Convenience - don't repeat `--profile` on every command
- ✅ Workflow focused - work on one disease at a time
- ✅ Natural mental model - like working in a project directory
- ✅ Reduces errors - don't accidentally mix flu and covid configs

### Combined Usage

Environments and profiles work together:

```bash
# Activate flu profile once
epycloud profile use flu

# Switch between environments easily
epycloud --env=dev verify --exp-id test
epycloud --env=dev run workflow --exp-id test
epycloud --env=prod run workflow --exp-id real-forecast

# Profile persists, environment is explicit each time
```

**Combined matrix:**

|                | dev              | prod             | local            |
|----------------|------------------|------------------|------------------|
| **flu**        | Test flu models  | Prod flu runs    | Local flu dev    |
| **covid**      | Test COVID       | Prod COVID       | Local COVID dev  |
| **rsv**        | Test RSV         | Prod RSV         | Local RSV dev    |

**Storage paths:**
```
gs://bucket/pipeline/dev/flu/test-sim/20251106-123456/
gs://bucket/pipeline/prod/flu/real-forecast/20251106-789012/
gs://bucket/pipeline/dev/covid/test-model/20251106-345678/
```

---

## Base Configuration

**File:** `~/.config/epymodelingsuite-cloud/config.yaml`

This is your default configuration, shared by all environments and profiles.

```yaml
# Default configuration (shared by all environments)

storage:
  dir_prefix: "pipeline/{environment}/{profile}"

google_cloud:
  project_id: your-gcp-project-id
  region: us-central1
  bucket_name: your-bucket-name

  batch:
    max_parallelism: 100
    task_count_per_node: 1

    stage_a:
      cpu_milli: 2000
      memory_mib: 4096
      machine_type: ""
      max_run_duration: 3600

    stage_b:
      cpu_milli: 2000
      memory_mib: 8192
      machine_type: ""
      max_run_duration: 36000

    stage_c:
      cpu_milli: 2000
      memory_mib: 8192
      machine_type: ""
      max_run_duration: 7200
      run_output_stage: true

docker:
  registry: "us-central1-docker.pkg.dev"
  repo_name: epymodelingsuite-repo
  image_name: epymodelingsuite
  image_tag: latest

github:
  modeling_suite_repo: mobs-lab/epymodelingsuite
  modeling_suite_ref: main

logging:
  level: INFO
  storage_verbose: true

workflow:
  retry_policy:
    max_attempts: 3
    backoff_seconds: 60
  notification:
    enabled: false
    email: null
```

---

## Environment Overrides

Environment-specific settings override base configuration.

### environments/dev.yaml

Development environment - lower resources, more verbose logging.

```yaml
# Development environment overrides

google_cloud:
  project_id: modeling-dev  # Override for dev

  batch:
    max_parallelism: 50     # Lower parallelism for dev

    stage_a:
      cpu_milli: 1000       # Smaller instances
      memory_mib: 2048

    stage_b:
      cpu_milli: 1000
      memory_mib: 4096
      max_run_duration: 7200  # 2 hours max for dev

logging:
  level: DEBUG              # More verbose in dev
  storage_verbose: true
```

### environments/prod.yaml

Production environment - full resources, less verbose.

```yaml
# Production environment overrides

google_cloud:
  project_id: modeling-prod  # Override for prod

  batch:
    max_parallelism: 100     # Full parallelism

    stage_b:
      cpu_milli: 4000        # Larger instances
      memory_mib: 16384
      machine_type: "c4d-standard-4"  # Compute-optimized

logging:
  level: INFO
  storage_verbose: false     # Less verbose in prod
```

### environments/local.yaml

Local development - filesystem only, no GCP.

```yaml
# Local development
# Note: dir_prefix still applies, but paths are ./local/bucket/{dir_prefix}/

logging:
  level: DEBUG
  storage_verbose: true
```

---

## Profile Configuration

Profile-specific settings for different diseases/projects.

### profiles/flu.yaml

```yaml
# Influenza forecasting profile
name: flu
description: Influenza forecasting models

# Flu-specific forecast repository
github:
  forecast_repo: mobs-lab/flu-forecast-epydemix

# Flu-specific resource requirements
google_cloud:
  batch:
    stage_b:
      cpu_milli: 2000
      memory_mib: 8192
    max_parallelism: 100
```

### profiles/covid.yaml

```yaml
# COVID-19 modeling profile
name: covid
description: COVID-19 modeling and forecasting

# COVID-specific forecast repository
github:
  forecast_repo: mobs-lab/covid-forecast

# COVID might need more resources
google_cloud:
  batch:
    stage_b:
      cpu_milli: 4000
      memory_mib: 16384
    max_parallelism: 200
```

### profiles/rsv.yaml

```yaml
# RSV modeling profile
name: rsv
description: RSV modeling

github:
  forecast_repo: mobs-lab/rsv-forecast

google_cloud:
  batch:
    stage_b:
      cpu_milli: 1000
      memory_mib: 4096
    max_parallelism: 50
```

---

## Configuration Merging

### Merge Order (Priority)

Configuration is merged in this order (highest priority last):

1. **Base config** - `config.yaml`
2. **Environment config** - `environments/{env}.yaml`
3. **Profile config** - `profiles/{profile}.yaml`
4. **Project config** - `./epycloud.yaml` (optional)
5. **Environment variables** - `EPYCLOUD_*`
6. **Command-line arguments** - `--project-id`, etc.

### Example Merge

**Active config for:** `--env=prod --profile=flu`

#### 1. Base config
```yaml
storage:
  dir_prefix: "pipeline/{environment}/{profile}"

google_cloud:
  project_id: my-default-project
  region: us-central1
  bucket_name: my-bucket
  batch:
    max_parallelism: 100
    stage_b:
      cpu_milli: 2000
      memory_mib: 8192

github:
  modeling_suite_repo: mobs-lab/epymodelingsuite
  modeling_suite_ref: main

logging:
  level: INFO
```

#### 2. + Production environment
```yaml
google_cloud:
  project_id: modeling-prod   # Override
  batch:
    stage_b:
      cpu_milli: 4000         # Override
      memory_mib: 16384       # Override
      machine_type: "c4d-standard-4"  # Add

logging:
  level: INFO                 # Keep
  storage_verbose: false      # Add
```

#### 3. + Flu profile
```yaml
github:
  forecast_repo: mobs-lab/flu-forecast-epydemix  # Add
```

#### 4. = Final merged config
```yaml
storage:
  dir_prefix: "pipeline/prod/flu"  # Interpolated

google_cloud:
  project_id: modeling-prod        # From prod env
  region: us-central1              # From base
  bucket_name: my-bucket           # From base
  batch:
    max_parallelism: 100           # From base
    stage_b:
      cpu_milli: 4000              # From prod env
      memory_mib: 16384            # From prod env
      machine_type: "c4d-standard-4"  # From prod env

github:
  modeling_suite_repo: mobs-lab/epymodelingsuite  # From base
  modeling_suite_ref: main                         # From base
  forecast_repo: mobs-lab/flu-forecast-epydemix   # From flu profile

docker:
  repo_name: epymodelingsuite-repo  # From base
  image_name: epymodelingsuite      # From base
  image_tag: latest                 # From base

logging:
  level: INFO                       # From prod env
  storage_verbose: false            # From prod env
```

### Template Interpolation

The `{environment}` and `{profile}` placeholders are replaced:

```yaml
# Template
storage:
  dir_prefix: "pipeline/{environment}/{profile}"

# For --env=prod --profile=flu
storage:
  dir_prefix: "pipeline/prod/flu"

# For --env=dev --profile=covid
storage:
  dir_prefix: "pipeline/dev/covid"
```

---

## Secrets Management

### secrets.yaml

**File:** `~/.config/epymodelingsuite-cloud/secrets.yaml`
**Permissions:** 0600 (user read/write only)

```yaml
# Secrets (never commit to git)

github:
  personal_access_token: github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)xxxxxxxxxxxxxxx

# Optional: GCP service account key
# google_cloud:
#   service_account_key_path: /path/to/key.json
```

**Automatically loaded** by config loader and merged into configuration.

### Environment Variables

Override any config value with environment variables:

```bash
# Pattern: EPYCLOUD_{SECTION}_{SUBSECTION}_{KEY}

export EPYCLOUD_GOOGLE_CLOUD_PROJECT_ID=override-project
export EPYCLOUD_GOOGLE_CLOUD_REGION=us-west1
export EPYCLOUD_GOOGLE_CLOUD_BUCKET_NAME=override-bucket
export EPYCLOUD_GOOGLE_CLOUD_BATCH_MAX_PARALLELISM=200

# GitHub PAT
export EPYCLOUD_GITHUB_PAT=github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)

# Or use secrets.yaml
```

---

## Examples

### Example 1: Development Workflow

```bash
# Activate flu profile
epycloud profile use flu

# Validate experiment configuration
epycloud --env=dev validate --exp-id weekly-forecast

# Run in dev environment
epycloud --env=dev run workflow --exp-id weekly-forecast

# Test locally
epycloud --env=local run workflow --exp-id test --local

# When ready, run in production
epycloud --env=prod run workflow --exp-id real-forecast
```

**Config used:**
- Base config + dev environment + flu profile
- Path: `gs://bucket/pipeline/dev/flu/weekly-forecast/...`
- GitHub token: From `secrets.yaml` or `GITHUB_TOKEN` env var (for validate)

### Example 2: Working on Multiple Diseases

```bash
# Morning: Work on flu
epycloud profile use flu
epycloud --env=dev verify --exp-id flu-week-45
epycloud --env=dev run workflow --exp-id flu-week-45

# Afternoon: Switch to COVID
epycloud profile use covid
epycloud --env=dev verify --exp-id covid-nov-2024
epycloud --env=dev run workflow --exp-id covid-nov-2024

# Check what profile you're on
epycloud profile current
# Output: covid
```

### Example 3: Production Deployment

```bash
# Activate flu profile
epycloud profile use flu

# Validate configuration
epycloud --env=prod validate --exp-id flu-prod-2024

# Deploy to production
epycloud --env=prod run workflow --exp-id flu-prod-2024 --wait

# Monitor
epycloud --env=prod status --watch
```

**Config used:**
- Base config + prod environment + flu profile
- Path: `gs://bucket/pipeline/prod/flu/flu-prod-2024/...`
- Resources: 4000 cpu_milli, 16384 memory_mib (from prod env)

### Example 4: Project-Local Overrides

For a special project with unique requirements:

```yaml
# ~/special-project/epycloud.yaml

# Override GCP settings for this project only
google_cloud:
  project_id: special-project-id
  bucket_name: special-data-bucket

# Override storage path
storage:
  dir_prefix: "special/{environment}/{profile}"
```

```bash
cd ~/special-project/

# Uses project-local config
epycloud --env=dev run workflow --exp-id test
# Path: gs://special-data-bucket/special/dev/flu/test/...
```

---

## Configuration Commands

### View Current Configuration

```bash
# Show full merged configuration
epycloud config show

# Show specific environment config
epycloud --env=prod config show

# Show specific profile config
epycloud --profile covid config show

# Get specific value
epycloud config get google_cloud.project_id
epycloud config get storage.dir_prefix
```

### Edit Configuration

```bash
# Edit base config
epycloud config edit

# Edit environment config
epycloud config edit --env prod

# Edit profile config
epycloud profile edit flu
```

### Validate Configuration

```bash
# Validate current config
epycloud config validate

# Validate specific environment
epycloud --env=prod config validate
```

---

## Best Practices

### 1. Keep Base Config Generic

Don't put environment-specific values in base config:

**Bad:**
```yaml
# config.yaml
google_cloud:
  project_id: modeling-dev  # Dev-specific!
```

**Good:**
```yaml
# config.yaml
google_cloud:
  project_id: my-default-project  # Generic default

# environments/dev.yaml
google_cloud:
  project_id: modeling-dev  # Dev override

# environments/prod.yaml
google_cloud:
  project_id: modeling-prod  # Prod override
```

### 2. Use Profiles for Disease-Specific Settings

Put disease-specific settings in profiles, not base config:

**Bad:**
```yaml
# config.yaml
github:
  forecast_repo: mobs-lab/flu-forecast  # Flu-specific!
```

**Good:**
```yaml
# profiles/flu.yaml
github:
  forecast_repo: mobs-lab/flu-forecast

# profiles/covid.yaml
github:
  forecast_repo: mobs-lab/covid-forecast
```

### 3. Never Commit Secrets

Always use `secrets.yaml` or environment variables for sensitive data:

**Bad:**
```yaml
# config.yaml (committed to git)
github:
  personal_access_token: github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)  # DON'T DO THIS!
```

**Good:**
```yaml
# secrets.yaml (gitignored)
github:
  personal_access_token: github_pat_xxxxx (or github_pat_xxxxx (or ghp_xxxxx for classic) for classic)
```

### 4. Use Environment Variables for CI/CD

For automation, use environment variables instead of files:

```bash
# CI/CD pipeline
export EPYCLOUD_ENV=prod
export EPYCLOUD_PROFILE=flu
export EPYCLOUD_GITHUB_PAT=$GITHUB_TOKEN

epycloud verify --exp-id weekly-forecast
epycloud run workflow --exp-id weekly-forecast
```

---

## Troubleshooting

### Check What Config is Being Used

```bash
# Show final merged config
epycloud --env=prod --profile=flu config show

# Show where config files are located
epycloud config path
```

### Verify Config Priority

```bash
# Test with increasing priority
epycloud config get google_cloud.project_id
# From base config

epycloud --env=prod config get google_cloud.project_id
# From prod environment override

export EPYCLOUD_GOOGLE_CLOUD_PROJECT_ID=override
epycloud config get google_cloud.project_id
# From environment variable override
```

### Debug Config Loading

```bash
# Verbose output shows config loading
epycloud --verbose config show

# Validate config syntax
epycloud config validate
```

---

**Document version:** 1.0
**Last updated:** 2025-11-06
