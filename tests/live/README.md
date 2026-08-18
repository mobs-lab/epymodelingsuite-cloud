# Live GCP smoke test

The live test is excluded from normal runs and creates one short-lived Google
Cloud Batch job. It uses `us-east5` unless `EPYCLOUD_LIVE_GCP_REGION` is set.

```bash
EPYCLOUD_RUN_LIVE_GCP=1 \
EPYCLOUD_LIVE_GCP_PROJECT=project-id \
EPYCLOUD_LIVE_GCP_IMAGE_URI=image-uri \
uv run pytest -m live_gcp tests/live
```

The active `gcloud` identity must be able to submit, describe, and delete Batch
jobs. Set `EPYCLOUD_LIVE_GCP_SERVICE_ACCOUNT` when the job must run as a
specific service account. The runnable executes only `/bin/bash -c true`; it
does not start the modeling pipeline or access GCS.
