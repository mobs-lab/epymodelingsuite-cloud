# Local Execution

This guide gets you running the pipeline locally in 10 minutes. No Google Cloud account is needed. For cloud deployment, see [Cloud Deployment](cloud-deployment.md).

## Prerequisites

### Docker

The pipeline runs inside Docker containers. You need a Docker-compatible runtime installed and running.

=== "macOS"

    We recommend [OrbStack](https://orbstack.dev/) for a lightweight, fast Docker engine on macOS.

    <!-- link-card: https://orbstack.dev/ | description=false -->

    Install via Homebrew or [download the installer](https://orbstack.dev/download):

    ```console
    $ brew install orbstack
    ```

    After installation, open OrbStack once to complete setup. It runs the Docker engine in the background.

    !!! note
        [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) also works if you have already installed it. However, note that the performance may not be as good as OrbStack.

=== "Linux"

    Install Docker Engine following the [official guide](https://docs.docker.com/engine/install/) for your distribution.

    ```console
    $ # Ubuntu/Debian
    $ sudo apt-get update
    $ sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
    ```

=== "Windows (WSL2)"

    Windows requires [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) with a Linux distribution. All commands in this guide should be run inside WSL2.

    <!-- link-card: https://learn.microsoft.com/en-us/windows/wsl/install -->

    1. Install WSL2 and Ubuntu (from PowerShell as Administrator):
    ```powershell
    wsl --install
    ```

    2. Install Docker Engine inside WSL2 following the [Linux instructions](https://docs.docker.com/engine/install/ubuntu/), or install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) with WSL2 backend enabled.

Verify Docker is running:

```console
$ docker info
$ docker compose version
```

### uv

We use [uv](https://docs.astral.sh/uv/) for package management. It handles Python version resolution automatically.

```console
$ # Install uv
$ curl -LsSf https://astral.sh/uv/install.sh | sh

$ # Verify
$ uv --version
```

### Disk Space

Ensure at least **10 GB free** for Docker images and build cache.

## Step 1: Install epycloud

Follow the [Installation Guide](installation.md) to install the `epycloud` CLI tool, then verify:

```console
$ epycloud --version
```

## Step 2: Configure epycloud

Initialize the configuration directory:

```console
$ epycloud config init
```

This creates `~/.config/epymodelingsuite-cloud/` with default configuration files, a `flu` profile, and sets it as the active profile. The profile resolves the `{profile}` placeholder used in storage paths (e.g., `pipeline/dev/flu/`). See [Configuration Guide](../user-guide/configuration/index.md) for details.

!!! tip "Skip Cloud Configuration"
    You don't need to set `project_id`, `bucket_name`, or other Google Cloud settings for local runs. The defaults are sufficient.

## Step 3: Build Docker image

Build the development image locally:

```console
$ epycloud build dev
```

This builds the Docker image without pushing to any registry. **First build takes 5-10 minutes** due to downloading dependencies.


## Step 4: Prepare test experiment

For local runs, we save experiment configurations in `./local/forecast/`:

```console
$ mkdir -p ./local/forecast/experiments/test-sim/config
```

**Option A**: Copy from experiment repository (if you have access):

```console
$ cp -r ~/Developer/my-flu-experiment-repo/experiments/test-sim ./local/forecast/experiments/
$ cp -r ~/Developer/my-flu-experiment-repo/common-data ./local/forecast/ 2>/dev/null || true
```

**Option B**: Create a minimal test configuration:

Create `./local/forecast/experiments/test-sim/config/basemodel_config.yaml` with a simple configuration (see [Configuration Guide](../user-guide/configuration/index.md) for examples).

## Step 5: Run workflow

Run the complete pipeline locally:

```console
$ epycloud run workflow --exp-id test-sim --local
```

This executes all three stages:

1. **Stage A (Builder)**: Generates input configurations
2. **Stage B (Runner)**: Processes simulations in parallel
3. **Stage C (Output)**: Aggregates results and generates CSV outputs

Results are saved to `./local/bucket/pipeline/flu/test-sim/{RUN_ID}/`

!!! warning "Local Execution Mode"
    The `--local` flag is required for local runs. Without it, epycloud will attempt to submit a cloud workflow.

## Step 6: View results

Check the output directory:

```console
$ ls -R ./local/bucket/pipeline/flu/test-sim/
```

View generated outputs:

```console
$ ls ./local/bucket/pipeline/flu/test-sim/*/outputs/
```

Output files include:
- `*.csv.gz` - Compressed CSV files with simulation results
- Quantiles, trajectories, metadata, etc.

## Common Local Commands

```console
# Configuration
$ epycloud config show                    # View current configuration
$ epycloud config edit                    # Edit base configuration

# Building
$ epycloud build dev                      # Build local image

# Running individual stages
$ epycloud run job --local --stage builder --exp-id test-sim
$ epycloud run job --local --stage runner --exp-id test-sim --run-id <RUN_ID> --task-index 0
$ epycloud run job --local --stage output --exp-id test-sim --run-id <RUN_ID> --num-tasks 2

# View logs
$ docker compose logs builder
$ docker compose logs runner
$ docker compose logs output
```

## Next Steps

<div class="grid cards" markdown>

-   :material-cloud:{ .lg .middle } **[Cloud Deployment](cloud-deployment.md)**

    ---

    Deploy infrastructure and run workflows on Google Cloud

-   :material-cog:{ .lg .middle } **[Configuration Guide](../user-guide/configuration/index.md)**

    ---

    Learn about profiles, environments, and advanced configuration

-   :material-bug:{ .lg .middle } **[Troubleshooting](../user-guide/troubleshooting/index.md)**

    ---

    Common issues and solutions for local development

</div>

## Troubleshooting

### Configuration not found

If you see "Configuration file not found" errors:

```console
$ epycloud config path         # Show config directory
$ epycloud config init          # Re-initialize if needed
```

### Docker image build fails

**Issue**: Docker not running

- **Solution**: Start your Docker engine (OrbStack, Docker Desktop, etc.)

**Issue**: Insufficient disk space

- **Solution**: Clean up Docker: `docker system prune -a`

### Local run fails

**Issue**: Experiment config not found

- **Solution**: Verify `./local/forecast/experiments/{EXP_ID}/config/` exists

**Issue**: Docker image doesn't exist

- **Solution**: Build the image first: `epycloud build dev`

**Issue**: Docker Compose not found

- **Solution**: Install Docker Compose: `docker compose version`

For more troubleshooting, see [Troubleshooting Guide](../user-guide/troubleshooting/index.md).
