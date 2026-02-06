# Prerequisites

Before deploying to Google Cloud, ensure you have the following tools installed and configured.

## Google Cloud Account

You need a Google Cloud account with billing enabled.

!!! note
    The steps below use `gcloud` CLI commands, but most of these can also be done through the [Google Cloud Console](https://console.cloud.google.com/) web interface.

1. Create an account at [cloud.google.com](https://cloud.google.com/) if you don't have one
2. Create a project or use an existing one:

    ```console
    $ gcloud projects create my-project-id --name="My Project"
    ```

    !!! info "Project ID vs. Project Name"
        - **Project ID** (`my-project-id`): A globally unique identifier used in CLI commands, APIs, and URLs. Cannot be changed after creation.
        - **Project Name** (`My Project`): A human-readable display label shown in the Cloud Console. Can be changed anytime.

        Choose a project ID that's meaningful to your team (e.g., `mobs-epi-pipeline`, `epi-modeling-prod`).

3. Link a billing account at [Billing Console](https://console.cloud.google.com/billing)

## gcloud CLI

The Google Cloud CLI (`gcloud`) is used for authentication, API management, and infrastructure operations.

<!-- link-card: https://docs.cloud.google.com/sdk/gcloud -->

### Install

=== "macOS"

    ```console
    $ brew install --cask google-cloud-sdk
    ```

    Or follow the [official installer](https://cloud.google.com/sdk/docs/install#mac).

=== "Linux"

    ```console
    $ curl https://sdk.cloud.google.com | bash
    $ exec -l $SHELL
    ```

    Or follow the [official guide](https://cloud.google.com/sdk/docs/install#linux).

=== "Windows (WSL2)"

    Install inside your WSL2 Linux distribution using the Linux instructions above.

### Configure

Set your default project and authenticate:

```console
$ gcloud config set project my-project-id
$ gcloud auth login
$ gcloud auth application-default login
```

### Enable Required APIs

The pipeline uses several Google Cloud services. Enable them all at once:

```console
$ gcloud services enable \
    compute.googleapis.com \
    batch.googleapis.com \
    workflows.googleapis.com \
    storage.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    secretmanager.googleapis.com
```

### IAM Permissions

To deploy and run the infrastructure, your user account needs these roles in addition to the Editor role (`roles/editor`):

| Role | Purpose |
|------|---------|
| **Project IAM Admin** (`roles/resourcemanager.projectIamAdmin`) | Manage project-level IAM bindings (Terraform) |
| **Secret Manager Admin** (`roles/secretmanager.admin`) | Manage IAM policies for secrets (Terraform) |
| **Service Account Admin** (`roles/iam.serviceAccountAdmin`) | Manage IAM policies on service accounts (Terraform) |
| **Cloud Build Editor** (`roles/cloudbuild.builds.editor`) | Submit and manage Cloud Build jobs (Docker builds) |

Grant these roles to your account:

```console
$ PROJECT_ID="my-project-id"
$ USER_EMAIL="user@example.com"

$ for ROLE in \
    roles/resourcemanager.projectIamAdmin \
    roles/secretmanager.admin \
    roles/iam.serviceAccountAdmin \
    roles/cloudbuild.builds.editor; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="user:$USER_EMAIL" \
    --role="$ROLE"
done
```

??? note "Common permission errors"
    | Error | Missing Role |
    |-------|-------------|
    | `Error 403: Policy update access denied` | Project IAM Admin or Secret Manager Admin |
    | `Permission 'iam.serviceAccounts.setIamPolicy' denied` | Service Account Admin |
    | `The caller does not have permission` (Cloud Build) | Cloud Build Editor |

    Ask your Google Cloud project administrator to grant these roles if needed.

## Terraform

Terraform manages the cloud infrastructure (GCS bucket references, Artifact Registry, service accounts, Cloud Workflows, etc.).

<!-- link-card: https://developer.hashicorp.com/terraform/intro | title="What is Terraform | Terraform | HashiCorp Developer" | description=false -->

### Install

=== "macOS"

    ```console
    $ brew tap hashicorp/tap
    $ brew install hashicorp/tap/terraform
    ```

=== "Linux"

    Follow the [official guide](https://developer.hashicorp.com/terraform/install#linux) for your distribution.

    For Ubuntu/Debian:

    ```console
    $ wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    $ echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    $ sudo apt update && sudo apt install terraform
    ```

### Verify

```console
$ terraform --version
Terraform v1.5.0+
```

Requires Terraform **1.5 or higher**.

## Experiment Repository

The pipeline clones a GitHub repository at runtime to read experiment configuration files.

### Repository structure
You need a repository with the following structure. Each folder under `experiments/` is an **experiment ID** (the value you pass to `--exp-id`):

```
my-flu-experiment-repo/
├── experiments/
│   └── my-experiment-001/    # <-- this is the experiment ID
│       └── config/
│           ├── basemodel.yaml
│           ├── modelset.yaml
│           └── output.yaml
├── common-data/          # Optional: shared data files
└── functions/            # Optional: custom Python modules
```

!!! tip "Experiment ID naming"
    The experiment ID is the folder path under `experiments/` and is used in storage paths and logs. It can be a single folder or nested directories. Choose a descriptive name, e.g., `smc-rmse-202606-hosp`, `flu-calibration-v2`, or `202606/smc-rmse-hosp`.

If you already have an experiment repository, you can skip ahead. Otherwise, follow these steps to create one:

### Create the repository

1. Create a new repository on [GitHub](https://github.com/new)
2. Clone it locally and set up the directory structure:

    ```console
    $ git clone https://github.com/your-org/my-flu-experiment-repo.git
    $ cd my-flu-experiment-repo
    $ mkdir -p experiments/my-experiment-001/config
    $ mkdir -p common-data
    $ mkdir -p functions
    ```

3. Add your experiment configuration files to `experiments/my-experiment-001/config/`
4. Commit and push:

    ```console
    $ git add .
    $ git commit -m "Add initial experiment config"
    $ git push origin main
    ```

The repository can be public or private (private requires a [GitHub PAT](#github-personal-access-token)).

!!! important
    Experiments must be pushed to the default branch (usually `main`) before running cloud workflows, since Stage A clones the repository at runtime. To use a different branch, set `forecast_repo_ref` in your config or pass `--forecast-repo-ref` when submitting a workflow.

## GitHub Personal Access Token

A GitHub PAT is required if you use **private repositories** (e.g., private experiment data repositories). It is used at runtime by Batch jobs to clone the repository. If all your repositories are public, you can skip this section.

### Create a Fine-Grained PAT

1. Go to **GitHub Settings** > **Developer settings** > **Personal access tokens** > [**Fine-grained tokens**](https://github.com/settings/personal-access-tokens/new)
2. Click **Generate new token**
3. Configure:
    - **Token name**: `epi-pipeline` (or similar)
    - **Expiration**: Set an appropriate expiration
    - **Repository access**: Select **Only select repositories** and add your private repositories (e.g., experiment data repository)
    - **Repository permissions**: Grant **Contents** > **Read-only**
4. Click **Generate token** and copy it immediately

!!! warning "Save Your Token"
    GitHub only shows the token once. Copy it before closing the page.

<!-- link-card: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens -->

### Store in epycloud Secrets

This is used for local Docker builds (`epycloud build dev`, `epycloud build local`). Cloud builds and cloud runs use Secret Manager instead (see below).

Add the PAT to your local epycloud configuration:

```console
$ epycloud config edit-secrets
```

Add your token:

```yaml
# secrets.yaml
github:
  pat: "github_pat_xxxxxxxxxxxx"
```

This file is stored at `~/.config/epymodelingsuite-cloud/secrets.yaml` with `0600` permissions (owner-only read/write).

### Store in Google Secret Manager

The PAT must also be stored in Secret Manager for cloud builds and Batch jobs to access:

```console
$ echo -n "github_pat_xxxxxxxxxxxx" | gcloud secrets create github-pat \
    --data-file=- \
    --project=my-project-id
```

To update an existing secret with a new token version:

```console
$ echo -n "github_pat_new_token" | gcloud secrets versions add github-pat \
    --data-file=- \
    --project=my-project-id
```

Verify the secret exists:

```console
$ gcloud secrets describe github-pat --project=my-project-id
```

!!! important
    - The secret name **must be `github-pat`** to match the Terraform configuration
    - Never commit the PAT to version control
    - Rotate the token regularly and set an appropriate expiration date

## GCS Bucket (Optional)

The pipeline stores artifacts and results in a Google Cloud Storage bucket. Terraform references an **existing** bucket rather than creating one, so if you don't already have a bucket, create one before deploying infrastructure.

```console
$ gsutil mb -p my-project-id -l us-central1 gs://my-bucket-name/
```

Or create one in the [Cloud Storage Console](https://console.cloud.google.com/storage/browser).

!!! tip
    If you already have a GCS bucket you'd like to use, you can skip this step and provide its name during [Setup](setup.md).

## Docker

Docker is required for building container images (both local development and pushing to Artifact Registry).


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

## epycloud CLI

If you haven't installed `epycloud` yet, follow the [Installation Guide](../installation.md).

Verify it's available:

```console
$ epycloud --version
```

## Checklist

Before proceeding to [Setup](setup.md), confirm:

- [ ] Google Cloud account with billing enabled
- [ ] `gcloud` CLI installed and authenticated
- [ ] Required APIs enabled
- [ ] IAM permissions granted
- [ ] Terraform 1.5+ installed
- [ ] GitHub PAT created and stored (only if using private repositories)
- [ ] GCS bucket created or existing bucket identified
- [ ] Experiment repository set up with configurations pushed
- [ ] Docker installed and running
- [ ] `epycloud` CLI installed
