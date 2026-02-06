# Cloud Build

Build and push Docker images using Google Cloud Build. This is the **recommended method for production**. The command returns immediately while the build runs asynchronously on Google's infrastructure.

## Quick Reference

```bash
epycloud build cloud                  # Submit build (async)
epycloud build status                 # View recent builds
epycloud build status --ongoing       # View active builds only
```

## Usage

```bash
epycloud build cloud
```

**Example output:**

```
Submitting build to Google Cloud Build...
Build ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Region: us-central1
Logs: https://console.cloud.google.com/cloud-build/builds/...

Build submitted successfully!

Monitor with:
  epycloud build status
  epycloud build status --ongoing
```

## Monitoring Build Status

```bash
# View all recent builds
epycloud build status

# View only active builds
epycloud build status --ongoing

# Stream logs for specific build (using gcloud directly)
gcloud builds log <BUILD_ID> --region=$REGION --stream

# View build details
gcloud builds describe <BUILD_ID> --region=$REGION
```

## Features

- **Asynchronous**: Submit and continue working immediately
- **Layer caching**: Faster rebuilds by reusing unchanged layers
- **Parallel execution**: Google handles resource allocation
- **Build history**: Track all builds in Cloud Console
- **No local resources**: Build runs on Google infrastructure

## Troubleshooting

**Build fails with "GITHUB_PAT" error:**

A GitHub PAT is only needed if you use private repositories. The `epymodelingsuite` package is public and does not require one. If you do need a PAT:

```bash
epycloud config edit-secrets

# Add your personal access token:
github:
  personal_access_token: ghp_xxxxxxxxxxxxxxxxxxxx

# Verify it's set
epycloud config show | grep personal_access_token
```

**Build fails with "permission denied":**

```bash
# Ensure Cloud Build service account has permissions
# Check IAM permissions in terraform/main.tf
epycloud terraform plan
epycloud terraform apply
```


## Related Documentation

- [CLI Reference - build](../../epycloud/build.md) - Build command
