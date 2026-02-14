# Environments

Environments are **configuration layers** that override the [base config](base.md). A common use case is maintaining separate settings for development vs. production, but they can represent any named set of overrides (a testing setup, a resource-tuned configuration, a specific modeling suite branch, etc.).

For example, in development you might use a `dev` Docker image tag and lower resource allocations, while production uses a pinned version tag and higher resources. Environments let you express this cleanly.

## Using environments

You select an environment **per command** using the `--env` flag. If you don't specify `--env`, it defaults to `default`.

```console
$ epycloud --env dev <command>          # Use dev environment (default)
$ epycloud --env prod <command>         # Use production environment
$ epycloud --env prod config show       # Show resolved prod config
```

## What belongs in an environment

Environment files only need to contain keys that differ from the [base config](base.md). Everything else is inherited. Typical settings include:

- Docker image tag (`docker.image_tag`)
- Modeling suite branch (`github.modeling_suite_ref`)
- Resource allocations (`google_cloud.batch.stage_b.cpu_milli`, etc.)
- Parallelism limits (`google_cloud.batch.max_parallelism`)

For project-specific settings (experiment repo, storage prefix), consider using [profiles](profiles.md) instead.

## Examples

A dev environment with lower resources and a development image:

```yaml title="environments/dev.yaml"
# Build epymodelingsuite from dev branch and tag the image as "dev"
docker:
  image_tag: "dev"

github:
  modeling_suite_ref: "dev"

# Lower resources for development
google_cloud:
  batch:
    max_parallelism: 50
    stage_b:
      cpu_milli: 1000
      memory_mib: 4096
```

A prod environment with pinned versions and higher resources:

```yaml title="environments/prod.yaml"
# Pin epymodelingsuite to a release tag
docker:
  image_tag: "v1.0.0"

github:
  modeling_suite_ref: "v1.0.0"

# Higher resources for production
google_cloud:
  batch:
    max_parallelism: 200
    stage_b:
      cpu_milli: 4000
      memory_mib: 16384
```

## Usage

```console
$ epycloud build cloud                              # Builds with dev env (default)
$ epycloud run workflow --exp-id test                # Runs with dev env

$ epycloud --env prod build cloud                   # Builds with prod env
$ epycloud --env prod run workflow --exp-id study    # Runs with prod env

$ epycloud --env prod config show                   # Inspect resolved config
```

For all available configuration keys, see the [Configuration Variables Reference](../../reference/configuration-variables.md).
