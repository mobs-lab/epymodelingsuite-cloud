.PHONY: build build-local build-dev run-dispatcher-local run-runner-local tf-init tf-plan tf-apply tf-destroy run-workflow clean help

# Default values - override with environment variables
PROJECT_ID ?= your-project
REGION ?= us-central1
REPO_NAME ?= epymodelingsuite-repo
BUCKET_NAME ?= your-bucket-name
IMAGE_NAME ?= epymodelingsuite
IMAGE_TAG ?= latest
GITHUB_FORECAST_REPO ?= owner/flu-forecast-epydemix  # GitHub repo (format: owner/repo)
GITHUB_MODELING_SUITE_REPO ?=  # Optional: GitHub modeling suite repo (format: owner/repo)
GITHUB_MODELING_SUITE_REF ?= main  # Branch or commit to build from
IMAGE := $(REGION)-docker.pkg.dev/$(PROJECT_ID)/$(REPO_NAME)/$(IMAGE_NAME):$(IMAGE_TAG)

# Workflow parameters
DIR_PREFIX ?= pipeline/flu/
# EXP_ID is required - no default value. Set via environment or command line.
# Example: EXP_ID=my-experiment make run-dispatcher-local

# Local execution parameters
TASK_INDEX ?= 0
NUM_RUNNERS ?= 10

# Build parameters
DISABLE_CACHE ?= false
CACHE_FLAG := $(if $(filter true,$(DISABLE_CACHE)),--no-cache,)

help:
	@echo "Available targets:"
	@echo "  build                - Build and push cloud image using Cloud Build (recommended)"
	@echo "  build-local          - Build cloud image locally and push to Artifact Registry"
	@echo "  build-dev            - Build local development image (no push, for docker-compose)"
	@echo "  run-dispatcher-local - Run dispatcher locally with docker-compose"
	@echo "  run-runner-local     - Run a single runner locally with docker-compose"
	@echo "  tf-init              - Initialize Terraform"
	@echo "  tf-plan              - Run Terraform plan"
	@echo "  tf-apply             - Apply Terraform configuration"
	@echo "  tf-destroy           - Destroy Terraform resources"
	@echo "  run-workflow         - Execute the workflow on Google Cloud"
	@echo "  clean                - Clean local artifacts"
	@echo ""
	@echo "Environment variables:"
	@echo "  REGION                  - GCP region (current: $(REGION))"
	@echo "  PROJECT_ID              - GCP project ID (current: $(PROJECT_ID))"
	@echo "  BUCKET_NAME             - GCS bucket name (current: $(BUCKET_NAME))"
	@echo "  IMAGE_NAME              - Docker image name (current: $(IMAGE_NAME))"
	@echo "  IMAGE_TAG               - Docker image tag (current: $(IMAGE_TAG))"
	@echo "  GITHUB_FORECAST_REPO         - GitHub forecast repo (current: $(GITHUB_FORECAST_REPO))"
	@echo "  GITHUB_MODELING_SUITE_REPO   - GitHub modeling suite repo (current: $(GITHUB_MODELING_SUITE_REPO))"
	@echo "  GITHUB_MODELING_SUITE_REF    - Modeling suite branch/ref (current: $(GITHUB_MODELING_SUITE_REF))"
	@echo "  DIR_PREFIX              - Base directory prefix (current: $(DIR_PREFIX))"
	@echo "  EXP_ID                  - Experiment ID (current: $(EXP_ID))"
	@echo "  TASK_INDEX              - Task index for local runner (current: $(TASK_INDEX))"
	@echo "  NUM_RUNNERS             - Number of runners to spawn (current: $(NUM_RUNNERS))"

build:
	@echo "Building and pushing image with Cloud Build..."
	@echo "Image: $(IMAGE)"
	gcloud builds submit --project=$(PROJECT_ID) --region $(REGION) --config cloudbuild.yaml \
	  --substitutions=_REGION=$(REGION),_REPO_NAME=$(REPO_NAME),_IMAGE_NAME=$(IMAGE_NAME),_IMAGE_TAG=$(IMAGE_TAG),_GITHUB_MODELING_SUITE_REPO=$(GITHUB_MODELING_SUITE_REPO),_GITHUB_MODELING_SUITE_REF=$(GITHUB_MODELING_SUITE_REF)

build-local:
	@echo "Building cloud image locally and pushing to Artifact Registry..."
	@echo "Image: $(IMAGE)"
	@if [ -n "$(GITHUB_MODELING_SUITE_REPO)" ]; then \
		if [ -z "$$GITHUB_PAT" ]; then \
			echo "Error: GITHUB_PAT environment variable must be set for builds with modeling suite"; \
			exit 1; \
		fi; \
		docker buildx build --platform linux/amd64 -t $(IMAGE) \
			--target cloud \
			--build-arg GITHUB_MODELING_SUITE_REPO=$(GITHUB_MODELING_SUITE_REPO) \
			--build-arg GITHUB_MODELING_SUITE_REF=$(GITHUB_MODELING_SUITE_REF) \
			--build-arg GITHUB_PAT=$$GITHUB_PAT \
			-f docker/Dockerfile . --push; \
	else \
		docker buildx build --platform linux/amd64 -t $(IMAGE) \
			--target cloud \
			-f docker/Dockerfile . --push; \
	fi

build-dev:
	@echo "Building local development image..."
	@echo "Target: local (no gcloud)"
	@if [ "$(DISABLE_CACHE)" = "true" ]; then echo "Cache: disabled (DISABLE_CACHE=true)"; else echo "Cache: enabled"; fi
	@if [ -n "$(GITHUB_MODELING_SUITE_REPO)" ]; then \
		echo "Repository: $(GITHUB_MODELING_SUITE_REPO) @ $(GITHUB_MODELING_SUITE_REF)"; \
	else \
		echo "Repository: not configured"; \
	fi
	@if [ -n "$(GITHUB_MODELING_SUITE_REPO)" ]; then \
		if [ -z "$$GITHUB_PAT" ]; then \
			echo "Error: GITHUB_PAT environment variable must be set for builds with modeling suite"; \
			echo "Run: source .env.local (after setting GITHUB_PAT in .env.local)"; \
			exit 1; \
		fi; \
		docker build $(CACHE_FLAG) -t $(IMAGE_NAME):local \
			--target local \
			--build-arg GITHUB_MODELING_SUITE_REPO=$(GITHUB_MODELING_SUITE_REPO) \
			--build-arg GITHUB_MODELING_SUITE_REF=$(GITHUB_MODELING_SUITE_REF) \
			--build-arg GITHUB_PAT=$$GITHUB_PAT \
			-f docker/Dockerfile .; \
	else \
		docker build $(CACHE_FLAG) -t $(IMAGE_NAME):local \
			--target local \
			-f docker/Dockerfile .; \
	fi
	@echo "✓ Local image built: $(IMAGE_NAME):local"
	@echo "  Use with: make run-dispatcher-local or make run-runner-local"

run-dispatcher-local:
	@echo "Running dispatcher locally with Docker Compose..."
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id make run-dispatcher-local"; \
		exit 1; \
	fi
	@echo "  Experiment ID: $(EXP_ID)"
	@echo ""
	@echo "Output will be in: ./local/bucket/$(EXP_ID)/<run_id>/inputs/"
	EXP_ID=$(EXP_ID) docker compose run --rm dispatcher
	@echo ""
	@echo "✓ Dispatcher complete. Check ./local/bucket/ for outputs."

run-runner-local:
	@echo "Running single runner locally (TASK_INDEX=$(TASK_INDEX))..."
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id make run-runner-local"; \
		exit 1; \
	fi
	@echo "  Reading from: ./local/bucket/$(EXP_ID)/*/inputs/"
	@echo "  Writing to: ./local/bucket/$(EXP_ID)/*/results/"
	EXP_ID=$(EXP_ID) TASK_INDEX=$(TASK_INDEX) docker compose run --rm runner
	@echo ""
	@echo "✓ Runner $(TASK_INDEX) complete."

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
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id make run-workflow"; \
		exit 1; \
	fi
	@echo "  Experiment ID: $(EXP_ID)"
	@echo "  GitHub Repo: $(GITHUB_FORECAST_REPO)"
	@BATCH_SA=$$(cd terraform && terraform output -raw batch_runtime_sa_email 2>/dev/null || echo "batch-runtime@$(PROJECT_ID).iam.gserviceaccount.com") && \
	gcloud workflows run epydemix-pipeline \
	  --location=$(REGION) \
	  --data='{"bucket":"$(BUCKET_NAME)","dirPrefix":"$(DIR_PREFIX)","exp_id":"$(EXP_ID)","githubForecastRepo":"$(GITHUB_FORECAST_REPO)","batchSaEmail":"'$$BATCH_SA'"}'

clean:
	@echo "Cleaning local artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"
