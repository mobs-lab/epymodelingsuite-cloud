# Cloud Deployment

Deploy the pipeline to Google Cloud and run workflows at scale.

!!! tip "Tips"
    Complete the [Quick Start (Local)](../local.md) guide first to familiarize yourself with epycloud before deploying to the cloud.

## What You'll Get

Deploying to Google Cloud enables:

- **Massive parallelism** - Run thousands of simulations concurrently
- **Automatic scaling** - Resources scale up/down based on workload
- **Managed infrastructure** - No servers to maintain
- **Cost optimization** - Pay only for compute time used

## Deployment Steps

<div class="grid cards" markdown>

-   :material-clipboard-check:{ .lg .middle } **[Prerequisites](prerequisites.md)**

    ---

    Install and configure gcloud CLI, Terraform, GitHub PAT, and Docker

-   :material-cloud-cog:{ .lg .middle } **[Setup](setup.md)**

    ---

    Configure epycloud and deploy infrastructure with Terraform

-   :material-rocket-launch:{ .lg .middle } **[Running Workflows](running.md)**

    ---

    Build Docker images and run your first cloud workflow

</div>

## Next Steps

After deploying to the cloud, see the [Google Cloud Guide](../../google-cloud-guide.md) for compute resource tuning and monitoring setup.
