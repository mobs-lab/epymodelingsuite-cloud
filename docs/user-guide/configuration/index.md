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


## Directory Structure

epycloud follows the XDG Base Directory specification:

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


## Configuration Components

- **[Base Configuration](base.md)**: Core settings in config.yaml
- **[Environments](environments.md)**: Environment-specific overrides (dev/prod/local)
- **[Profiles](profiles.md)**: Project-specific settings (flu/covid/rsv)
- **[Secrets](secrets.md)**: Sensitive credentials and environment variables


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
