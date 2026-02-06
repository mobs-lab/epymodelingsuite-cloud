# Configuration

Learn how to configure epycloud for different environments, projects, and use cases.

## Overview

epycloud uses a **hierarchical, stacked configuration system**. Layers are listed from highest to lowest priority. Each layer overrides the values defined in the layers below it, and unspecified values are inherited from the layers below.

<div style="text-align: center;">

``` mermaid
---
config:
  theme: base
  themeVariables:
    fontSize: 14px
---
block-beta
  columns 1

  cli["CLI Arguments
  --project-id, --env, etc."]
  envvar["Environment Variables
  EPYCLOUD_*"]
  project["Local Project Config (optional)
  ./epycloud.yaml"]
  profile["Active Profile
  profiles/flu.yaml"]
  env["Environment
  environments/dev.yaml"]
  base["Base Config
  config.yaml"]

  style base fill:#f5f5f5,stroke:#9e9e9e
  style env fill:#e8f5e9,stroke:#2e7d32
  style profile fill:#e3f2fd,stroke:#1565c0
  style project fill:#fff3e0,stroke:#e65100
  style envvar fill:#fce4ec,stroke:#c62828
  style cli fill:#f3e5f5,stroke:#6a1b9a
```

</div>


## Configuration components

| File | Location | Purpose |
|------|----------|---------|
| [Base config](base.md) | `~/.config/epymodelingsuite-cloud/config.yaml` | Shared defaults that apply to all environments and profiles |
| [Environments](environments.md) | `~/.config/epymodelingsuite-cloud/environments/{env}.yaml` | Infrastructure differences between dev, prod, and local |
| [Profiles](profiles.md) | `~/.config/epymodelingsuite-cloud/profiles/{profile}.yaml` | Disease or project-specific settings (flu, covid, rsv) |
| Project config | `./epycloud.yaml` | Repository-local overrides, checked into version control (optional) |
| [Secrets](secrets.md) | `~/.config/epymodelingsuite-cloud/secrets.yaml` | Credentials such as GitHub PAT (0600 permissions) |

For a complete listing of all configuration keys, see the [Configuration Variables Reference](../../reference/configuration-variables.md).


## Directory structure

epycloud follows the XDG Base Directory specification. All configuration files are saved at `XDG_CONFIG_HOME`.

```
~/.config/epymodelingsuite-cloud/      # XDG_CONFIG_HOME
├── config.yaml                        # Base configuration
├── secrets.yaml                       # Sensitive credentials
├── active_profile                     # Current active profile name
├── environments/                      # Environment-specific overrides
│   ├── default.yaml                   # Default environment
│   ├── dev.yaml                       # Development overrides
│   ├── prod.yaml                      # Production overrides
│   └── local.yaml                     # Local testing
└── profiles/                          # Project/disease-specific settings
    ├── flu.yaml                       # Flu forecasting
    ├── covid.yaml                     # COVID modeling
    └── rsv.yaml                       # RSV modeling

~/.local/share/epymodelingsuite-cloud/ # XDG_DATA_HOME
└── cache/                             # Runtime cache

~/.cache/epymodelingsuite-cloud/       # XDG_CACHE_HOME
└── build-cache/                       # Build artifacts cache
```

## Example

The following shows how a base config, a dev environment, and a flu profile are merged together. Values from higher-priority layers take precedence, while everything else is inherited from the base.

The base config defines common defaults shared across all environments and profiles:

```yaml title="config.yaml"
google_cloud:
  project_id: "my-project"
  region: "us-central1"
  bucket_name: "my-bucket"
docker:
  image_tag: "latest"
  image_name: "epymodelingsuite"
github:
  modeling_suite_ref: "main"
pipeline:
  max_parallelism: 100
```

The dev environment overrides only the values that differ from the base. Here, we build the Docker image from a feature branch of the modeling suite and tag it `dev`:

```yaml title="environments/dev.yaml"
docker:
  image_tag: "dev"
github:
  modeling_suite_ref: "feature-branch"
```

The flu profile adds project-specific settings like the experiment repository and storage prefix:

```yaml title="profiles/flu.yaml"
github:
  forecast_repo: "mobs-lab/flu-forecast-epydemix"
pipeline:
  dir_prefix: "pipeline/flu/"
```

The final merged result combines all layers. Values from higher-priority layers take precedence:

```yaml title="Merged result (base + dev + flu)"
google_cloud:
  project_id: "my-project"           # From base
  region: "us-central1"              # From base
  bucket_name: "my-bucket"           # From base
docker:
  image_tag: "dev"                   # From dev environment ✓
  image_name: "epymodelingsuite"     # From base
github:
  modeling_suite_ref: "feature-branch"             # From dev environment ✓ (overrides "main")
  forecast_repo: "mobs-lab/flu-forecast-epydemix"  # From flu profile ✓
pipeline:
  max_parallelism: 100               # From base
  dir_prefix: "pipeline/flu/"        # From flu profile ✓
```


## When each config is used

Configuration is read at three different points: **infrastructure deployment**, **image building**, and **workflow execution**. Depending on what you change, you may need to redeploy infrastructure, rebuild the Docker image, or simply run a new workflow.

For example:

| Setting | Takes effect after |
|-------------------|--------------------------|
| Google Cloud project, region, bucket | `epycloud terraform apply` |
| Batch resource defaults (CPU, memory, machine type) | `epycloud terraform apply` (but can be overridden per run) |
| Modeling suite version (`github.modeling_suite_ref`) | `epycloud build` |
| Docker image tag, experiment repo, parallelism | Next `epycloud run workflow` (no redeploy needed) |

For the full breakdown of which keys are read at each point, see [When each config is used](../../reference/configuration-variables.md#when-each-config-is-used) in the reference.


## Best practices

1. **Keep base config minimal**: Only common settings
2. **Use environments for infrastructure**: Docker image tags, resources, branches
3. **Use profiles for projects**: Disease-specific settings, repos
4. **Never commit secrets**: Use `secrets.yaml` with `.gitignore`
5. **Validate before deployment**: Run `epycloud config validate`


## Next steps

- Set up [base configuration](base.md)
- Create [profiles](profiles.md) for your projects
- Configure [secrets](secrets.md) securely
- Learn about [environments](environments.md)

<div class="grid cards" markdown>

-   :material-format-list-bulleted:{ .lg .middle } **[Configuration Variables Reference](../../reference/configuration-variables.md)**

    ---

    Complete listing of all configuration keys, types, and default values

</div>
