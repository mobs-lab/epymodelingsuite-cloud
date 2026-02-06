# Running Workflows

Build Docker images and execute your first workflow on Google Cloud.

!!! tip "Tips"
    Make sure you've completed [Setup](setup.md) and have infrastructure deployed before continuing.

## Step 1: Build Docker image

The pipeline runs inside Docker containers on Google Cloud. The Docker image packages the `epymodelingsuite` library and pipeline scripts into a portable environment that Cloud Batch uses to execute each stage. You need to build and push this image before running any cloud workflow.

Submit an asynchronous build to Google Cloud Build:

```console
$ epycloud build cloud
```

This submits the build to Cloud Build and returns immediately with a build ID. The image is built remotely and pushed to Artifact Registry automatically.

Monitor build status:

```console
$ epycloud build status
```

Builds typically take few minutes. Wait for the build to succeed before proceeding.

You can also check build status and view built images in the Cloud Console:

- [Cloud Build history](https://console.cloud.google.com/cloud-build/builds) - Build logs and status
- [Artifact Registry](https://console.cloud.google.com/artifacts) - Built Docker images

See [`epycloud build`](../../epycloud/build.md) for all build options including local builds.

???+ note "When to rebuild"
    - After **updating `epymodelingsuite`** (new version or different branch)
    - After **changing pipeline scripts** in `docker/scripts/`
    - When using an **environment** with a different `modeling_suite_ref` or `image_tag` (see [Using Environments](../../epycloud/build.md#using-environments))

## Step 2: Prepare experiment configuration

Your experiment configuration must exist in the experiment repository (configured in your profile's `forecast_repo`). See [Experiment Repository](prerequisites.md#experiment-repository) for how to set up the repository.

### Push to the repository

Since Stage A clones the repository at runtime, your experiment must be on the default branch (usually `main`). We recommend using a branch and pull request workflow:

```console
$ cd /path/to/experiment-repo
$ git checkout -b add-my-experiment-001
$ git add experiments/my-experiment-001/
$ git commit -m "Add my-experiment-001 config"
$ git push origin add-my-experiment-001
```

Then create a pull request on GitHub, review the configuration, and merge to `main`.

### Validate configuration (optional)

Before submitting, you can [validate](../../epycloud/validate.md) your experiment configuration locally:

```console
$ epycloud validate --exp-id my-experiment-001
```

This checks that the configuration files are valid and can be parsed by the pipeline.

## Step 3: Submit workflow

We are finally ready to submit the workflow to cloud.

```console
$ epycloud run workflow --exp-id my-experiment-001
```

This submits a Cloud Workflow that orchestrates the full pipeline:

1. **Stage A (Builder)**: Generates task inputs from experiment configuration
2. **Stage B (Runner)**: Runs simulations/calibrations in parallel
3. **Stage C (Output)**: Aggregates results into CSV outputs

The command returns an execution ID:

```
Execution ID: abcdef12-3456-7890
```

## Step 4: Monitor progress

Check the status of active workflows and jobs:

```console
$ epycloud status
```

Use watch mode for continuous monitoring:

```console
$ epycloud status -w
```

See [`epycloud status`](../../epycloud/status.md) for more options.

### Additional monitoring commands

View detailed status of a specific execution:

```console
$ epycloud workflow describe abcdef12-3456-7890
```

Stream logs in real-time:

```console
$ epycloud logs --exp-id my-experiment-001 --follow
```

Filter logs by stage:

```console
$ epycloud logs --exp-id my-experiment-001 --stage A
$ epycloud logs --exp-id my-experiment-001 --stage B
$ epycloud logs --exp-id my-experiment-001 --stage C
```

## Step 5: View results

Results are stored in GCS at the path configured by your `dir_prefix` and experiment ID.

List runs:

```console
$ gsutil ls gs://my-bucket-name/pipeline/flu/my-experiment-001/
```

Download results:

```console
$ gsutil -m cp -r gs://my-bucket-name/pipeline/flu/my-experiment-001/RUN-ID/outputs/ ./results/
```

Output files include:

- `quantiles_*.csv.gz` - Quantile summaries
- `trajectories_*.csv.gz` - Individual trajectories
- `metadata_*.csv.gz` - Run metadata

## Managing workflows

### Cancel a workflow

Cancel the workflow and its associated batch jobs:

```console
$ epycloud workflow cancel abcdef12-3456-7890
```

Cancel only the workflow (keep batch jobs running):

```console
$ epycloud workflow cancel abcdef12-3456-7890 --only-workflow
```

### View history

```console
$ epycloud workflow list --exp-id my-experiment-001 --limit 50
```

### Export logs

```console
$ epycloud --no-color logs --exp-id my-experiment-001 --tail 0 > logs.txt
```

## Troubleshooting

### Build fails

**"Permission denied" during Cloud Build**

- Verify your user has the Cloud Build Editor role (see [Prerequisites](prerequisites.md#iam-permissions))

**Build succeeds but image not found**

- Check that the image tag matches your config: `epycloud config show | grep image_tag`

### Workflow submission fails

**"Workflow not found"**

- Infrastructure not deployed. Run `epycloud terraform apply`.

**"Docker image not found"**

- Image not built or tag mismatch. Run `epycloud build cloud`.

**"Permission denied"**

- Verify APIs are enabled and service accounts have correct permissions

### Stage B tasks fail

**Tasks timeout or run out of memory**

- Increase resources in config (`stage_b.cpu_milli`, `stage_b.memory_mib`)
- Run `epycloud terraform apply` to update

### High costs

**Unexpected billing charges**

- Check for stuck workflows: `epycloud workflow list`
- Cancel long-running workflows
- Review [Cloud Console Batch jobs](https://console.cloud.google.com/batch/jobs)

## Next Steps

- **[Workflow Monitoring](../../user-guide/monitoring/workflows.md)**: Detailed monitoring guide
