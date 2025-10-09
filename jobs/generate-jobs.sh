#!/usr/bin/env bash
# Generate job JSON files from templates using environment variables
# Usage: source ../.env && ./jobs/generate-jobs.sh

set -e

# Check if required variables are set
: "${PROJECT_ID:?PROJECT_ID not set}"
: "${REGION:?REGION not set}"
: "${REPO_NAME:?REPO_NAME not set}"
: "${BUCKET_NAME:?BUCKET_NAME not set}"
: "${IMAGE_NAME:=epymodelingsuite}"
: "${IMAGE_TAG:=latest}"

# Construct full image URI
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

# Get Batch SA email from Terraform or construct it
if [ -f terraform/terraform.tfstate ]; then
  BATCH_SA_EMAIL=$(cd terraform && terraform output -raw batch_runtime_sa_email 2>/dev/null || echo "batch-runtime@${PROJECT_ID}.iam.gserviceaccount.com")
else
  BATCH_SA_EMAIL="batch-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
fi

# Default values for job parameters (can be overridden)
COUNT=${COUNT:-10}
SEED=${SEED:-1234}
OUT_PREFIX=${OUT_PREFIX:-"inputs/"}
IN_PREFIX=${IN_PREFIX:-"inputs/"}
RESULTS_PREFIX=${RESULTS_PREFIX:-"results/"}
TASK_COUNT=${TASK_COUNT:-10}
PARALLELISM=${PARALLELISM:-100}

echo "Generating job templates..."
echo "  Image URI: ${IMAGE_URI}"
echo "  Bucket: ${BUCKET_NAME}"
echo "  Batch SA: ${BATCH_SA_EMAIL}"

# Generate Stage A
envsubst < jobs/stage-a.json.template > jobs/stage-a.json <<EOF
IMAGE_URI=${IMAGE_URI}
BUCKET_NAME=${BUCKET_NAME}
BATCH_SA_EMAIL=${BATCH_SA_EMAIL}
COUNT=${COUNT}
SEED=${SEED}
OUT_PREFIX=${OUT_PREFIX}
EOF

echo "  ✓ Generated jobs/stage-a.json"

# Generate Stage B
OUT_PREFIX=${RESULTS_PREFIX} envsubst < jobs/stage-b.json.template > jobs/stage-b.json <<EOF
IMAGE_URI=${IMAGE_URI}
BUCKET_NAME=${BUCKET_NAME}
BATCH_SA_EMAIL=${BATCH_SA_EMAIL}
TASK_COUNT=${TASK_COUNT}
PARALLELISM=${PARALLELISM}
IN_PREFIX=${IN_PREFIX}
OUT_PREFIX=${RESULTS_PREFIX}
EOF

echo "  ✓ Generated jobs/stage-b.json"
echo ""
echo "Job templates generated successfully!"
echo ""
echo "To run them:"
echo "  gcloud batch jobs submit stage-a-manual-\$(date +%s) --location=${REGION} --config=jobs/stage-a.json"
echo "  gcloud batch jobs submit stage-b-manual-\$(date +%s) --location=${REGION} --config=jobs/stage-b.json"
