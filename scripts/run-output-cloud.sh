#!/usr/bin/env bash
# Submit Stage C (output generation) job to Google Cloud Batch
# Matches the exact configuration used in the workflow
#
# Usage:
#   EXP_ID=test-flu RUN_ID=20251017-0145-xxxxxx NUM_TASKS=10 ./scripts/run-output-cloud.sh
#
# Required environment variables:
#   - EXP_ID: Experiment ID
#   - RUN_ID: Run ID
#   - NUM_TASKS: Number of result files from Stage B
#   - PROJECT_ID: GCP project ID
#   - REGION: GCP region
#   - BUCKET_NAME: GCS bucket name
#   - REPO_NAME: Artifact Registry repository name
#   - IMAGE_NAME: Docker image name
#   - IMAGE_TAG: Docker image tag
#
# Optional environment variables:
#   - DIR_PREFIX: Directory prefix in GCS (default: "")
#   - GITHUB_FORECAST_REPO: GitHub repo for forecast data (default: "")
#   - STAGE_C_CPU_MILLI: CPU in milli-cores (default: 2000)
#   - STAGE_C_MEMORY_MIB: Memory in MiB (default: 8192)
#   - STAGE_C_MACHINE_TYPE: Machine type (default: "")
#   - STAGE_C_MAX_RUN_DURATION: Maximum task duration in seconds (default: 7200)

set -euo pipefail

# Validate required parameters
: "${EXP_ID:?ERROR: EXP_ID is required}"
: "${RUN_ID:?ERROR: RUN_ID is required}"
: "${NUM_TASKS:?ERROR: NUM_TASKS is required}"

# Validate required environment variables
: "${PROJECT_ID:?ERROR: PROJECT_ID not set}"
: "${REGION:?ERROR: REGION not set}"
: "${BUCKET_NAME:?ERROR: BUCKET_NAME not set}"
: "${REPO_NAME:?ERROR: REPO_NAME not set}"
: "${IMAGE_NAME:?ERROR: IMAGE_NAME not set}"
: "${IMAGE_TAG:?ERROR: IMAGE_TAG not set}"

# Optional variables with defaults
DIR_PREFIX="${DIR_PREFIX:-}"
GITHUB_FORECAST_REPO="${GITHUB_FORECAST_REPO:-}"
STAGE_C_CPU_MILLI="${STAGE_C_CPU_MILLI:-2000}"
STAGE_C_MEMORY_MIB="${STAGE_C_MEMORY_MIB:-8192}"
STAGE_C_MACHINE_TYPE="${STAGE_C_MACHINE_TYPE:-}"
STAGE_C_MAX_RUN_DURATION="${STAGE_C_MAX_RUN_DURATION:-7200}"

# Construct image URI
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

# Get Batch SA email from Terraform or construct it
if [ -f terraform/terraform.tfstate ]; then
  BATCH_SA_EMAIL=$(cd terraform && terraform output -raw batch_runtime_sa_email 2>/dev/null || echo "batch-runtime@${PROJECT_ID}.iam.gserviceaccount.com")
else
  BATCH_SA_EMAIL="batch-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
fi

# Generate unique job ID
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
JOB_ID="stagec-manual-${TIMESTAMP}"

echo "========================================="
echo "Submitting Stage C (output) job to Cloud Batch"
echo "========================================="
echo "Job ID:          ${JOB_ID}"
echo "Experiment ID:   ${EXP_ID}"
echo "Run ID:          ${RUN_ID}"
echo "Num Tasks:       ${NUM_TASKS}"
echo ""
echo "Configuration:"
echo "  Project:       ${PROJECT_ID}"
echo "  Region:        ${REGION}"
echo "  Bucket:        ${BUCKET_NAME}"
echo "  Dir Prefix:    ${DIR_PREFIX}"
echo "  Image:         ${IMAGE_URI}"
echo "  Service Acct:  ${BATCH_SA_EMAIL}"
echo "  CPU (milli):   ${STAGE_C_CPU_MILLI}"
echo "  Memory (MiB):  ${STAGE_C_MEMORY_MIB}"
if [ -n "${STAGE_C_MACHINE_TYPE}" ]; then
  echo "  Machine Type:  ${STAGE_C_MACHINE_TYPE}"
fi
echo "========================================="
echo ""

# Build the JSON configuration matching workflow.yaml Stage C
# This matches the exact configuration from terraform/workflow.yaml lines 242-306

# Build the taskSpec JSON
TASK_SPEC=$(cat <<EOF
{
  "runnables": [
    {
      "container": {
        "imageUri": "${IMAGE_URI}",
        "entrypoint": "/bin/bash",
        "commands": [
          "/scripts/run_output.sh"
        ]
      }
    }
  ],
  "environment": {
    "variables": {
      "EXECUTION_MODE": "cloud",
      "GCS_BUCKET": "${BUCKET_NAME}",
      "DIR_PREFIX": "${DIR_PREFIX}",
      "EXP_ID": "${EXP_ID}",
      "RUN_ID": "${RUN_ID}",
      "NUM_TASKS": "${NUM_TASKS}",
      "GITHUB_FORECAST_REPO": "${GITHUB_FORECAST_REPO}",
      "GCLOUD_PROJECT_ID": "${PROJECT_ID}",
      "GITHUB_PAT_SECRET": "github-pat",
      "FORECAST_REPO_DIR": "/data/forecast/"
    }
  },
  "computeResource": {
    "cpuMilli": ${STAGE_C_CPU_MILLI},
    "memoryMib": ${STAGE_C_MEMORY_MIB}
  },
  "maxRunDuration": "${STAGE_C_MAX_RUN_DURATION}s"
}
EOF
)

# Build allocation policy with optional machine type
if [ -n "${STAGE_C_MACHINE_TYPE}" ]; then
  # Check if machine type is C4D (requires hyperdisk)
  if [[ "${STAGE_C_MACHINE_TYPE}" == c4d-* ]]; then
    # C4D machine types require Hyperdisk (hyperdisk-balanced or hyperdisk-extreme)
    # C4D does NOT support regular Persistent Disks (pd-ssd, pd-balanced, etc.)
    ALLOCATION_POLICY=$(cat <<EOF
{
  "serviceAccount": {
    "email": "${BATCH_SA_EMAIL}"
  },
  "instances": [
    {
      "installGpuDrivers": false,
      "policy": {
        "machineType": "${STAGE_C_MACHINE_TYPE}",
        "provisioningModel": "STANDARD",
        "bootDisk": {
          "type": "hyperdisk-balanced",
          "sizeGb": 50
        }
      }
    }
  ]
}
EOF
)
  else
    ALLOCATION_POLICY=$(cat <<EOF
{
  "serviceAccount": {
    "email": "${BATCH_SA_EMAIL}"
  },
  "instances": [
    {
      "policy": {
        "machineType": "${STAGE_C_MACHINE_TYPE}"
      }
    }
  ]
}
EOF
)
  fi
else
  ALLOCATION_POLICY=$(cat <<EOF
{
  "serviceAccount": {
    "email": "${BATCH_SA_EMAIL}"
  }
}
EOF
)
fi

# Build the complete job JSON
JOB_JSON=$(cat <<EOF
{
  "labels": {
    "component": "epymodelingsuite",
    "stage": "output",
    "exp_id": "${EXP_ID}",
    "run_id": "${RUN_ID}",
    "managed-by": "manual"
  },
  "taskGroups": [
    {
      "taskCount": 1,
      "taskSpec": ${TASK_SPEC}
    }
  ],
  "logsPolicy": {
    "destination": "CLOUD_LOGGING"
  },
  "allocationPolicy": ${ALLOCATION_POLICY}
}
EOF
)

# Write JSON to temp file for debugging
TEMP_JSON=$(mktemp)
echo "${JOB_JSON}" > "${TEMP_JSON}"

echo "Submitting job to Cloud Batch..."
echo ""

# Submit the job
gcloud batch jobs submit "${JOB_ID}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --config="${TEMP_JSON}"

# Clean up temp file
rm -f "${TEMP_JSON}"

echo ""
echo "========================================="
echo "✓ Job submitted successfully!"
echo "========================================="
echo ""
echo "Job Name: projects/${PROJECT_ID}/locations/${REGION}/jobs/${JOB_ID}"
echo ""
echo "Monitor with:"
echo "  gcloud batch jobs describe ${JOB_ID} --location=${REGION} --project=${PROJECT_ID}"
echo ""
echo "View logs:"
echo "  gcloud logging read \"resource.type=batch.googleapis.com/Job AND labels.job_uid=\\\"${JOB_ID}\\\"\" --limit=50 --project=${PROJECT_ID}"
echo ""
echo "List tasks:"
echo "  gcloud batch tasks list --job=${JOB_ID} --location=${REGION} --project=${PROJECT_ID}"
echo ""
