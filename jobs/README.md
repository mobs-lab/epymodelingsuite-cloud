# Manual Batch Job Templates

These JSON files allow you to run Stage A or B independently without Workflows.

## Generating Job Templates

The `*.json.template` files use environment variables. Generate concrete JSON files:

```bash
# Load environment variables
source .env

# Generate stage-a.json and stage-b.json
./jobs/generate-jobs.sh

# Or with custom parameters
COUNT=20 SEED=5678 ./jobs/generate-jobs.sh
```

**Template variables:**
- `IMAGE_URI` - Docker image (from PROJECT_ID, REGION, REPO_NAME, IMAGE_NAME, IMAGE_TAG)
- `BUCKET_NAME` - GCS bucket
- `BATCH_SA_EMAIL` - Service account (from Terraform or constructed)
- `COUNT` - Number of inputs (Stage A)
- `SEED` - Random seed (Stage A)
- `OUT_PREFIX` - Output prefix (Stage A)
- `IN_PREFIX` - Input prefix (Stage B)
- `TASK_COUNT` - Number of parallel tasks (Stage B)
- `PARALLELISM` - Max concurrent tasks (Stage B)

## Usage

### Run Stage A (Generate Inputs)

```bash
# After generating templates
gcloud batch jobs submit stage-a-manual-$(date +%s) \
  --location=$REGION \
  --config=jobs/stage-a.json
```

### Run Stage B (Process Tasks)

**Important**: Stage B requires Stage A outputs to exist first!

```bash
# After generating templates and running Stage A
gcloud batch jobs submit stage-b-manual-$(date +%s) \
  --location=$REGION \
  --config=jobs/stage-b.json
```

## Monitor Jobs

```bash
# List jobs
gcloud batch jobs list --location=$REGION

# Describe a specific job
gcloud batch jobs describe JOB_NAME --location=$REGION

# View logs
gcloud logging read "resource.type=batch.googleapis.com/Job AND resource.labels.job_uid=JOB_UID" \
  --limit=50 \
  --format=json
```

## When to Use

- **Development/Testing**: Test individual stages without running full workflow
- **Debugging**: Run with modified parameters or environment variables
- **Emergency**: Rerun failed stages manually
- **Experimentation**: Quick iterations on stage logic

## Note

Workflows creates jobs dynamically and doesn't use these templates. These are purely for manual/debugging purposes.

## Files

- `stage-a.json.template` - Template for Stage A job
- `stage-b.json.template` - Template for Stage B job
- `stage-a.json` - Generated Stage A job (gitignored)
- `stage-b.json` - Generated Stage B job (gitignored)
- `generate-jobs.sh` - Script to generate JSON from templates
