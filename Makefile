.PHONY: build build-local tf-init tf-plan tf-apply tf-destroy run-workflow clean help

# Default values - override with environment variables
PROJECT_ID ?= your-project
REGION ?= us-central1
REPO_NAME ?= epymodelingsuite-repo
BUCKET_NAME ?= your-bucket-name
IMAGE_NAME ?= epymodelingsuite
IMAGE_TAG ?= latest
GITHUB_FORECAST_REPO ?= owner/flu-forecast-epydemix  # GitHub repo (format: owner/repo)
IMAGE := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO_NAME)/$(IMAGE_NAME):$(IMAGE_TAG)

# Workflow parameters
RUN_COUNT ?= 10
RUN_SEED ?= 1234
DIR_PREFIX ?= pipeline/flu/
SIM_ID ?= default-sim

help:
	@echo "Available targets:"
	@echo "  build          - Build and push Docker image using Cloud Build"
	@echo "  build-local    - Build Docker image locally and push"
	@echo "  tf-init        - Initialize Terraform"
	@echo "  tf-plan        - Run Terraform plan"
	@echo "  tf-apply       - Apply Terraform configuration"
	@echo "  tf-destroy     - Destroy Terraform resources"
	@echo "  run-workflow   - Execute the workflow with sample parameters"
	@echo "  clean          - Clean local artifacts"
	@echo ""
	@echo "Environment variables:"
	@echo "  REGION                  - GCP region (current: $(REGION))"
	@echo "  PROJECT_ID              - GCP project ID (current: $(PROJECT_ID))"
	@echo "  BUCKET_NAME             - GCS bucket name (current: $(BUCKET_NAME))"
	@echo "  IMAGE_NAME              - Docker image name (current: $(IMAGE_NAME))"
	@echo "  IMAGE_TAG               - Docker image tag (current: $(IMAGE_TAG))"
	@echo "  GITHUB_FORECAST_REPO    - GitHub repo (current: $(GITHUB_FORECAST_REPO))"
	@echo "  RUN_COUNT               - Number of tasks (current: $(RUN_COUNT))"
	@echo "  RUN_SEED                - Random seed (current: $(RUN_SEED))"
	@echo "  DIR_PREFIX              - Base directory prefix (current: $(DIR_PREFIX))"
	@echo "  SIM_ID                  - Simulation ID (current: $(SIM_ID))"

build:
	@echo "Building and pushing image with Cloud Build..."
	@echo "Image: $(IMAGE)"
	gcloud builds submit --project=$(PROJECT_ID) --region $(REGION) --config cloudbuild.yaml \
	  --substitutions=_REGION=$(REGION),_REPO_NAME=$(REPO_NAME),_IMAGE_NAME=$(IMAGE_NAME),_IMAGE_TAG=$(IMAGE_TAG)

build-local:
	@echo "Building locally..."
	@echo "Image: $(IMAGE)"
	docker buildx build --platform linux/amd64 -t $(IMAGE) -f docker/Dockerfile . --push

tf-init:
	@echo "Initializing Terraform..."
	cd terraform && terraform init

tf-plan:
	@echo "Planning Terraform changes..."
	cd terraform && terraform plan \
	  -var="project_id=$(PROJECT_ID)" \
	  -var="region=$(REGION)" \
	  -var="repo_name=$(REPO_NAME)" \
	  -var="bucket_name=$(BUCKET_NAME)" \
	  -var="image_name=$(IMAGE_NAME)" \
	  -var="image_tag=$(IMAGE_TAG)" \
	  -var="github_forecast_repo=$(GITHUB_FORECAST_REPO)"

tf-apply:
	@echo "Applying Terraform configuration..."
	cd terraform && terraform apply \
	  -var="project_id=$(PROJECT_ID)" \
	  -var="region=$(REGION)" \
	  -var="repo_name=$(REPO_NAME)" \
	  -var="bucket_name=$(BUCKET_NAME)" \
	  -var="image_name=$(IMAGE_NAME)" \
	  -var="image_tag=$(IMAGE_TAG)" \
	  -var="github_forecast_repo=$(GITHUB_FORECAST_REPO)"

tf-destroy:
	@echo "WARNING: This will destroy all Terraform-managed resources!"
	@echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
	@sleep 5
	cd terraform && terraform destroy \
	  -var="project_id=$(PROJECT_ID)" \
	  -var="region=$(REGION)" \
	  -var="repo_name=$(REPO_NAME)" \
	  -var="bucket_name=$(BUCKET_NAME)" \
	  -var="image_name=$(IMAGE_NAME)" \
	  -var="image_tag=$(IMAGE_TAG)" \
	  -var="github_forecast_repo=$(GITHUB_FORECAST_REPO)"

run-workflow:
	@echo "Running workflow..."
	@echo "  Count: $(RUN_COUNT)"
	@echo "  Seed: $(RUN_SEED)"
	@echo "  Sim ID: $(SIM_ID)"
	@echo "  GitHub Repo: $(GITHUB_FORECAST_REPO)"
	@BATCH_SA=$$(cd terraform && terraform output -raw batch_runtime_sa_email 2>/dev/null || echo "batch-runtime@$(PROJECT_ID).iam.gserviceaccount.com") && \
	gcloud workflows run epydemix-pipeline \
	  --location=$(REGION) \
	  --data='{"count":$(RUN_COUNT),"seed":$(RUN_SEED),"bucket":"$(BUCKET_NAME)","dirPrefix":"$(DIR_PREFIX)","sim_id":"$(SIM_ID)","githubForecastRepo":"$(GITHUB_FORECAST_REPO)","batchSaEmail":"'$$BATCH_SA'"}'

clean:
	@echo "Cleaning local artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"
