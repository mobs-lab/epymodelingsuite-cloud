#!/usr/bin/env bash
# Submit a single Stage B task to Google Cloud Batch
# Matches the exact configuration used in the workflow
#
# Usage:
#   EXP_ID=test-flu RUN_ID=20251017-0145-xxxxxx TASK_INDEX=3 ./scripts/run-task-cloud.sh
#
# Required environment variables:
#   - EXP_ID: Experiment ID
#   - RUN_ID: Run ID
#   - TASK_INDEX: Task index to run (0-based)
#   - PROJECT_ID: GCP project ID
#   - REGION: GCP region
#   - BUCKET_NAME: GCS bucket name
#   - REPO_NAME: Artifact Registry repository name
#   - IMAGE_NAME: Docker image name
#   - IMAGE_TAG: Docker image tag
#
# Optional environment variables:
#   - DIR_PREFIX: Directory prefix in GCS (default: "")
#   - STAGE_B_CPU_MILLI: CPU in milli-cores (default: 2000)
#   - STAGE_B_MEMORY_MIB: Memory in MiB (default: 8192)
#   - STAGE_B_MACHINE_TYPE: Machine type (default: "")
#   - STAGE_B_MAX_RUN_DURATION: Maximum task duration in seconds (default: 36000)

set -euo pipefail

# Validate required parameters
: "${EXP_ID:?ERROR: EXP_ID is required}"
: "${RUN_ID:?ERROR: RUN_ID is required}"
: "${TASK_INDEX:?ERROR: TASK_INDEX is required}"

# Validate required environment variables
: "${PROJECT_ID:?ERROR: PROJECT_ID not set}"
: "${REGION:?ERROR: REGION not set}"
: "${BUCKET_NAME:?ERROR: BUCKET_NAME not set}"
: "${REPO_NAME:?ERROR: REPO_NAME not set}"
: "${IMAGE_NAME:?ERROR: IMAGE_NAME not set}"
: "${IMAGE_TAG:?ERROR: IMAGE_TAG not set}"

# Optional variables with defaults
DIR_PREFIX="${DIR_PREFIX:-}"
STAGE_B_CPU_MILLI="${STAGE_B_CPU_MILLI:-2000}"
STAGE_B_MEMORY_MIB="${STAGE_B_MEMORY_MIB:-8192}"
STAGE_B_MACHINE_TYPE="${STAGE_B_MACHINE_TYPE:-}"
STAGE_B_MAX_RUN_DURATION="${STAGE_B_MAX_RUN_DURATION:-36000}"

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
JOB_ID="stageb-manual-task${TASK_INDEX}-${TIMESTAMP}"

echo "========================================="
echo "Submitting single Stage B task to Cloud Batch"
echo "========================================="
echo "Job ID:          ${JOB_ID}"
echo "Experiment ID:   ${EXP_ID}"
echo "Run ID:          ${RUN_ID}"
echo "Task Index:      ${TASK_INDEX}"
echo ""
echo "Configuration:"
echo "  Project:       ${PROJECT_ID}"
echo "  Region:        ${REGION}"
echo "  Bucket:        ${BUCKET_NAME}"
echo "  Dir Prefix:    ${DIR_PREFIX}"
echo "  Image:         ${IMAGE_URI}"
echo "  Service Acct:  ${BATCH_SA_EMAIL}"
echo "  CPU (milli):   ${STAGE_B_CPU_MILLI}"
echo "  Memory (MiB):  ${STAGE_B_MEMORY_MIB}"
if [ -n "${STAGE_B_MACHINE_TYPE}" ]; then
  echo "  Machine Type:  ${STAGE_B_MACHINE_TYPE}"
fi
echo "========================================="
echo ""

# Build the JSON configuration matching workflow.yaml Stage B
# This matches the exact configuration from terraform/workflow.yaml lines 143-190

# Build the taskSpec JSON
TASK_SPEC=$(cat <<EOF
{
  "runnables": [
    {
      "container": {
        "imageUri": "${IMAGE_URI}",
        "entrypoint": "python3",
        "commands": [
          "-u",
          "/scripts/main_runner.py"
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
      "BATCH_TASK_INDEX": "${TASK_INDEX}"
    }
  },
  "computeResource": {
    "cpuMilli": ${STAGE_B_CPU_MILLI},
    "memoryMib": ${STAGE_B_MEMORY_MIB}
  },
  "maxRunDuration": "${STAGE_B_MAX_RUN_DURATION}s"
}
EOF
)

# Build allocation policy with optional machine type
if [ -n "${STAGE_B_MACHINE_TYPE}" ]; then
  ALLOCATION_POLICY=$(cat <<EOF
{
  "serviceAccount": {
    "email": "${BATCH_SA_EMAIL}"
  },
  "instances": [
    {
      "policy": {
        "machineType": "${STAGE_B_MACHINE_TYPE}"
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
    "stage": "runner",
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
