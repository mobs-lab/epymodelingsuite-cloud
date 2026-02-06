# epycloud build

Build Docker images for pipeline execution.

## Usage

```bash
epycloud build [MODE] [OPTIONS]
```

## Description

Creates Docker images containing the pipeline execution environment. Supports three build modes:

- **cloud** - Asynchronous builds using Google Cloud Build (production)
- **local** - Local builds with push to Artifact Registry
- **dev** - Local-only development builds (no push)

## Build Modes

### cloud

Build using Google Cloud Build service (default, asynchronous).

```bash
epycloud build cloud [CONTEXT] [OPTIONS]
epycloud build  # cloud is default
```

**Arguments:**
- `CONTEXT` - Build context directory (default: project root)

**Options:**
- `--cache` - Enable build cache (disabled by default)
- `--tag TAG` - Custom image tag
- `--wait` - Wait for build completion
- `-f DOCKERFILE, --file DOCKERFILE` - Path to Dockerfile (default: docker/Dockerfile)

Returns build ID immediately. Monitor with `epycloud build status`.

### local

Build locally using Docker and push to Artifact Registry.

```bash
epycloud build local [CONTEXT] [OPTIONS]
```

**Arguments:**
- `CONTEXT` - Build context directory (default: docker/)

**Options:**
- `--no-cache` - Disable build cache
- `--tag TAG` - Custom image tag
- `--no-push` - Don't push to registry
- `-f DOCKERFILE, --file DOCKERFILE` - Path to Dockerfile (default: docker/Dockerfile)

Synchronous build using local Docker daemon.

### dev

Build locally for development (no push by default).

```bash
epycloud build dev [CONTEXT] [OPTIONS]
```

**Arguments:**
- `CONTEXT` - Build context directory (default: docker/)

**Options:**
- `--cache` - Enable build cache (disabled by default)
- `--tag TAG` - Custom image tag
- `--push` - Push to registry (optional)
- `-f DOCKERFILE, --file DOCKERFILE` - Path to Dockerfile (default: docker/Dockerfile)

Fast iteration for local testing.

## Build Status

Check build status:

```bash
epycloud build status [OPTIONS]
```

**Options:**
- `--limit LIMIT` - Maximum number of builds to display (default: 10)
- `--ongoing` - Show only active builds (QUEUED, WORKING)

## Using Environments

The global `--env` flag selects an environment configuration that overrides build settings like `image_tag` and `modeling_suite_ref`. This is the standard way to build images for different branches or purposes.

**Create an environment file** at `~/.config/epymodelingsuite-cloud/environments/<name>.yaml`:

```yaml
# environments/feature1.yaml
docker:
  image_tag: feature1
github:
  modeling_suite_ref: feature1
```

**Build with that environment:**

```bash
epycloud --env feature1 build cloud    # Cloud build with feature1 settings
epycloud --env feature1 build dev      # Dev build with feature1 settings
```

This builds the Docker image using the `feature1` branch of `epymodelingsuite` and tags the image as `feature1`. Without `--env`, the base config values are used.

See [Environments](../user-guide/configuration/environments.md) for details on environment configuration.

## Examples

```bash
# Cloud build (default, asynchronous)
epycloud build
epycloud build cloud

# Cloud build and wait for completion
epycloud build cloud --wait

# Cloud build with cache enabled
epycloud build cloud --cache

# Cloud build with custom tag
epycloud build cloud --tag v1.2.3

# Cloud build with custom Dockerfile
epycloud build cloud -f custom/Dockerfile

# Local build and push
epycloud build local

# Local build without pushing
epycloud build local --no-push

# Dev build (local only, no push)
epycloud build dev

# Dev build with cache enabled
epycloud build dev --cache

# Build with environment overrides
epycloud --env feature1 build cloud
epycloud --env prod build cloud
epycloud --env dev build dev

# Check build status
epycloud build status
epycloud build status --limit 20
epycloud build status --ongoing
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Build failed |

## Related Commands

- [`epycloud run`](run.md) - Run workflows with built images
- [`epycloud config`](config.md) - Configure Docker and Artifact Registry settings

## See Also

- [Building Images Guide](../user-guide/building-images.md) - Detailed build instructions
- [Docker Images Architecture](../architecture/docker-images.md) - Image structure
