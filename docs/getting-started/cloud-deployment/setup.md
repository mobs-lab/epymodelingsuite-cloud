# Setup

Configure your epycloud settings and deploy cloud infrastructure with Terraform.

!!! tip "Tips"
    Make sure you've completed all steps in [Prerequisites](prerequisites.md) before continuing.

## What you'll set up

By the end of this guide, you will have:

1. **epycloud configured** with your Google Cloud project, Docker registry, and GitHub repositories
2. **Cloud infrastructure deployed** via Terraform, including:
    - Artifact Registry for Docker images
    - Service accounts with scoped IAM permissions
    - Cloud Workflows for pipeline orchestration
    - Monitoring dashboards and budget alerts

## Step 1: Initialize configuration

If you already ran `epycloud config init` during the [Local Execution](../local.md) guide, you can skip this step and go straight to [Step 2](#step-2-configure-for-cloud).

```console
$ epycloud config init
```

This creates `~/.config/epymodelingsuite-cloud/` with default configuration files and sets up a `flu` profile. See [Configuration Guide](../../user-guide/configuration/index.md) for details.

## Step 2: Configure for Cloud

Open the base configuration:

```console
$ epycloud config edit
```

### Google Cloud settings

Set your project, region, and bucket:

```yaml
# config.yaml
google_cloud:
  project_id: "my-project-id"
  region: "us-central1"
  bucket_name: "my-bucket-name" # GCS bucket needs to be setup in advance
```

- `project_id`: Your Google Cloud project ID (from [Prerequisites](prerequisites.md#google-cloud-account))
- `region`: The region for compute resources ([available regions](https://docs.cloud.google.com/compute/docs/regions-zones#available))
- `bucket_name`: An existing GCS bucket for storing pipeline artifacts and results (from [Prerequisites](prerequisites.md#gcs-bucket-optional)). Terraform does not create a new one.

### Docker settings

Configure the Artifact Registry repository and image:

```yaml
docker:
  repo_name: "my-docker-repo"
  image_name: "epymodelingsuite"
  image_tag: "latest"
```

- `repo_name`: Name for the Artifact Registry repository (Terraform creates this)
- `image_name`: Docker image name
- `image_tag`: Image tag (use `latest` or a version string)

### GitHub settings

Configure the modeling suite repository used during Docker builds:

```yaml
github:
  modeling_suite_repo: "mobs-lab/epymodelingsuite"
  modeling_suite_ref: "main"
```

- `modeling_suite_repo`: `epymodelingsuite` package installed during Docker build. Defaults to `mobs-lab/epymodelingsuite`. Change this if you are using a fork.
- `modeling_suite_ref`: Branch, tag, or commit to install (default: `main`)

### Profile settings

The experiment repository is configured per profile, since different projects use different repositories. Edit your active profile:

```console
$ epycloud config edit --profile=flu
```

```yaml
# profiles/flu.yaml
github:
  forecast_repo: "owner/experiment-repo"

pipeline:
  dir_prefix: "pipeline/flu/"
```

- `forecast_repo`: Experiment data repository cloned at runtime by Batch jobs
- `dir_prefix`: Storage path prefix for this project's artifacts and results. This prefix is prepended to all storage paths:

    ```
    gs://{bucket_name}/{dir_prefix}{exp_id}/{run_id}/
    ```

    For example, with `dir_prefix: "pipeline/flu/"` and experiment `test-sim`:

    ```
    gs://my-bucket-name/pipeline/flu/test-sim/20260205-143052-a1b2c3d4/
    ├── builder-artifacts/    # Stage A outputs (input_0000.pkl, ...)
    ├── runner-artifacts/     # Stage B outputs (result_0000.pkl, ...)
    └── outputs/              # Stage C outputs (*.csv.gz)
    ```

    The base config template uses `pipeline/{environment}/{profile}` which resolves automatically (e.g., `pipeline/dev/flu/`). You can override it per profile to a fixed value like `pipeline/flu/`.

See [Profiles](../../user-guide/configuration/profiles.md) for more details.

### Verify configuration

Make sure your profile is active, then verify the merged configuration:

```console
$ epycloud profile use flu
$ epycloud config show
```

Check that all config files are loaded:

```
Loaded from:
  - ~/.config/epymodelingsuite-cloud/config.yaml
  - ~/.config/epymodelingsuite-cloud/environments/default.yaml
  - ~/.config/epymodelingsuite-cloud/profiles/flu.yaml
  - ~/.config/epymodelingsuite-cloud/secrets.yaml
```

## Step 3: Deploy infrastructure

### Configure Terraform backend

Before initializing, you need to edit the Terraform state backend to point to your own GCS bucket. Open `terraform/main.tf` and update the `backend "gcs"` block:

```hcl
terraform {
  backend "gcs" {
    bucket = "your-bucket-name"        # (1)!
    prefix = "pipeline-terraform/state"
  }
}
```

1. Replace with your GCS bucket name. This is where Terraform stores its state file. Terraform's `backend` block [does not support variables](https://developer.hashicorp.com/terraform/language/backend#backend-configuration), so this must be edited directly.

### Initialize Terraform

```console
$ epycloud terraform init
```

### Review plan

Preview the resources that will be created:

```console
$ epycloud terraform plan
```

### Deploy

```console
$ epycloud terraform apply
```

### What's Deployed

After `terraform apply` completes, the following resources are provisioned:

| Resource | Purpose |
|----------|---------|
| **Artifact Registry** | Docker image repository |
| **Service Accounts** | `batch_runtime_sa` (Batch jobs), `workflows_runner_sa` (Workflows) |
| **IAM Bindings** | Storage, Secret Manager, Batch, and Logging permissions |
| **Cloud Workflows** | Pipeline orchestration (from `terraform/workflow.yaml`) |
| **Monitoring Dashboards** | CPU/memory dashboards for each pipeline stage |
| **Budget Alerts** | Monthly budget threshold notifications |

## Next Steps

- **[Running Workflows](running.md)**: Build images and run your first cloud workflow
