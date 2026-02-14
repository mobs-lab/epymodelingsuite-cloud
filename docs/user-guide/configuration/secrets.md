# Secrets

Secrets are sensitive credentials stored separately from the rest of the configuration. For local builds, secrets are kept in `secrets.yaml`. For cloud builds and runs, the credentials are read from [Google Cloud Secret Manager](#cloud-google-cloud-secret-manager).

Currently the only secret is the **GitHub Personal Access Token (PAT)**, used to access private repositories (e.g., a private experiment data repository).

!!! note "When is a GitHub PAT needed?"
    A PAT is only required if you use **private repositories**. The `epymodelingsuite` package is public and does not require one. If all your repositories are public (including the experiment repository), you can skip this page.

## Setting up secrets

The setup depends on whether you are running locally or on the cloud.

### Local (secrets.yaml)

The credentials in `secrets.yaml` are used during local Docker builds (passed as a build argument to clone private repositories).

For initial setup and editing,

```console
$ epycloud config init                 # Creates secrets.yaml (if it doesn't exist)
$ epycloud config edit-secrets         # Open secrets.yaml in $EDITOR
```

```yaml title="~/.config/epymodelingsuite-cloud/secrets.yaml"
github:
  personal_access_token: "github_pat_xxxxxxxxxxxxx"
```

After saving the file, confirm that PAT is loaded:
```console
$ epycloud config show                 # Verify config (secrets are masked)
```

!!! danger "Warning"
    The secrets file (`secrets.yaml`) contains credentials and should never be committed to version control (e.g., git).

### Cloud (Google Cloud Secret Manager)

In cloud mode, credentials are stored securely in [Google Cloud Secret Manager](https://docs.cloud.google.com/secret-manager/docs/overview). Batch jobs fetch it at runtime to clone private repositories.

**Secret name:** `github-pat`

```console
$ PROJECT_ID=$(epycloud config get google_cloud.project_id)

# Create the secret
$ echo -n "your_github_pat" | gcloud secrets create github-pat \
    --data-file=- \
    --project=${PROJECT_ID}

# Update the secret value
$ echo -n "new_github_pat" | gcloud secrets versions add github-pat \
    --data-file=- \
    --project=${PROJECT_ID}
```

The service account running Batch jobs must have the `secretmanager.secretAccessor` role.

## GitHub PAT

A GitHub Personal Access Token (PAT) is a credential that grants access to GitHub repositories on your behalf. epycloud uses it to clone private repositories during Docker builds (locally) and at runtime (in the cloud). We recommend using [fine-grained tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#fine-grained-personal-access-tokens), which let you scope access to specific repositories with minimal permissions.

<!-- link-card: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
    | description=false
-->

To create one:

1. Go to [GitHub > Settings > Developer settings > Fine-grained tokens](https://github.com/settings/tokens?type=beta)
2. Click **Generate new token**
3. Configure the token:
    - **Token name**: something descriptive (e.g., `epycloud`)
    - **Expiration**: set a reasonable expiration and rotate regularly
    - **Repository access**: select only the specific private repositories you need (e.g., experiment data repo)
    - **Permissions**: Contents (read-only)
4. Click **Generate token** and copy the value (it starts with `github_pat_`)

## Security best practices

- Never commit `secrets.yaml` to version control
- Rotate GitHub PATs regularly
- Use fine-grained PATs with minimal permissions
- PAT is passed to Docker as a build argument (not persisted in image layers)
