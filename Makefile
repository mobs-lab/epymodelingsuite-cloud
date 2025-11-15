# ============================================================================
# DEPRECATED: This Makefile is deprecated in favor of the epycloud CLI
#
# Please use the following commands instead:
#
#   make build              →  uv run epycloud build cloud
#   make build-local        →  uv run epycloud build local
#   make build-dev          →  uv run epycloud build dev
#   make run-builder-local  →  uv run epycloud run local builder --exp-id X
#   make run-task-local     →  uv run epycloud run local runner --exp-id X --run-id Y --task-index N
#   make run-output-local   →  uv run epycloud run local output --exp-id X --run-id Y --num-tasks N
#   make run-workflow       →  uv run epycloud run workflow --exp-id X
#   make tf-init            →  uv run epycloud terraform init
#   make tf-plan            →  uv run epycloud terraform plan
#   make tf-apply           →  uv run epycloud terraform apply
#   make tf-destroy         →  uv run epycloud terraform destroy
#
# This file will be removed in a future version.
# ============================================================================

.PHONY: build build-local build-dev run-builder-local run-task-local run-output-local tf-init tf-plan tf-apply tf-destroy run-workflow clean help

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
MAX_PARALLELISM ?= 100
# EXP_ID is required - no default value. Set via environment or command line.
# Example: EXP_ID=my-experiment make run-builder-local
# RUN_ID is optional - auto-generated if not provided

# Batch machine configuration
STAGE_A_CPU_MILLI ?= 2000
STAGE_A_MEMORY_MIB ?= 4096
STAGE_A_MACHINE_TYPE ?=
STAGE_A_MAX_RUN_DURATION ?= 3600
STAGE_B_CPU_MILLI ?= 2000
STAGE_B_MEMORY_MIB ?= 8192
STAGE_B_MACHINE_TYPE ?=
STAGE_B_MAX_RUN_DURATION ?= 36000
STAGE_C_CPU_MILLI ?= 2000
STAGE_C_MEMORY_MIB ?= 8192
STAGE_C_MACHINE_TYPE ?=
STAGE_C_MAX_RUN_DURATION ?= 7200
TASK_COUNT_PER_NODE ?= 1

# Local execution parameters
TASK_INDEX ?= 0
NUM_RUNNERS ?= 10

# Build parameters
DISABLE_CACHE ?= false
CACHE_FLAG := $(if $(filter true,$(DISABLE_CACHE)),--no-cache,)

help:
	@echo "Available targets:"
	@echo "  build              - Build and push cloud image using Cloud Build (recommended)"
	@echo "  build-local        - Build cloud image locally and push to Artifact Registry"
	@echo "  build-dev          - Build local development image (no push, for docker-compose)"
	@echo "  run-builder-local  - Run builder locally with docker-compose"
	@echo "  run-task-local     - Run a single task locally with docker-compose"
	@echo "  run-output-local   - Run output generation locally with docker-compose"
	@echo "  tf-init            - Initialize Terraform"
	@echo "  tf-plan            - Run Terraform plan"
	@echo "  tf-apply           - Apply Terraform configuration"
	@echo "  tf-destroy         - Destroy Terraform resources"
	@echo "  run-workflow       - Execute the workflow on Google Cloud"
	@echo "  clean              - Clean local artifacts"
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
	@echo "  MAX_PARALLELISM         - Max parallel tasks (current: $(MAX_PARALLELISM))"
	@echo "  EXP_ID                  - Experiment ID (current: $(EXP_ID))"
	@echo "  RUN_ID                  - Run ID (current: $(RUN_ID))"
	@echo "  TASK_INDEX              - Task index for local runner (current: $(TASK_INDEX))"
	@echo "  NUM_RUNNERS             - Number of runners to spawn (current: $(NUM_RUNNERS))"
	@echo "  STAGE_A_CPU_MILLI       - Stage A CPU in milli-cores (current: $(STAGE_A_CPU_MILLI))"
	@echo "  STAGE_A_MEMORY_MIB      - Stage A memory in MiB (current: $(STAGE_A_MEMORY_MIB))"
	@echo "  STAGE_A_MACHINE_TYPE    - Stage A machine type (current: $(STAGE_A_MACHINE_TYPE))"
	@echo "  STAGE_B_CPU_MILLI       - Stage B CPU in milli-cores (current: $(STAGE_B_CPU_MILLI))"
	@echo "  STAGE_B_MEMORY_MIB      - Stage B memory in MiB (current: $(STAGE_B_MEMORY_MIB))"
	@echo "  STAGE_B_MACHINE_TYPE    - Stage B machine type (current: $(STAGE_B_MACHINE_TYPE))"
	@echo "  STAGE_B_MAX_RUN_DURATION - Stage B max duration in seconds (current: $(STAGE_B_MAX_RUN_DURATION))"
	@echo "  STAGE_C_CPU_MILLI       - Stage C CPU in milli-cores (current: $(STAGE_C_CPU_MILLI))"
	@echo "  STAGE_C_MEMORY_MIB      - Stage C memory in MiB (current: $(STAGE_C_MEMORY_MIB))"
	@echo "  STAGE_C_MACHINE_TYPE    - Stage C machine type (current: $(STAGE_C_MACHINE_TYPE))"
	@echo "  STAGE_C_MAX_RUN_DURATION - Stage C max duration in seconds (current: $(STAGE_C_MAX_RUN_DURATION))"
	@echo "  TASK_COUNT_PER_NODE     - Max tasks per VM (current: $(TASK_COUNT_PER_NODE))"

build:
	@echo "Building and pushing image with Cloud Build (async)..."
	@echo "Image: $(IMAGE)"
	@BUILD_ID=$$(gcloud builds submit --project=$(PROJECT_ID) --region $(REGION) --config cloudbuild.yaml --async \
	  --substitutions=_REGION=$(REGION),_REPO_NAME=$(REPO_NAME),_IMAGE_NAME=$(IMAGE_NAME),_IMAGE_TAG=$(IMAGE_TAG),_GITHUB_MODELING_SUITE_REPO=$(GITHUB_MODELING_SUITE_REPO),_GITHUB_MODELING_SUITE_REF=$(GITHUB_MODELING_SUITE_REF) \
	  --format="value(id)") && \
	echo "" && \
	echo "✓ Build submitted successfully!" && \
	echo "  Build ID: $$BUILD_ID" && \
	echo "" && \
	echo "Monitor with:" && \
	echo "  gcloud builds describe $$BUILD_ID --region=$(REGION)" && \
	echo "  gcloud builds log $$BUILD_ID --region=$(REGION) --stream" && \
	echo "  gcloud builds list --region=$(REGION) --ongoing"

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
	@echo "  Use with: make run-builder-local or make run-runner-local"

run-builder-local:
	@echo "Running builder locally with Docker Compose..."
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id make run-builder-local"; \
		exit 1; \
	fi
	@echo "  Experiment ID: $(EXP_ID)"
	@if [ -n "$(RUN_ID)" ]; then \
		echo "  Run ID: $(RUN_ID)"; \
	fi
	@echo ""
	@echo "Output will be in: ./local/bucket/$(EXP_ID)/<run_id>/builder-artifacts/"
	EXP_ID=$(EXP_ID) RUN_ID=$(RUN_ID) docker compose run --rm builder
	@echo ""
	@echo "✓ Builder complete. Check ./local/bucket/ for outputs."

run-task-local:
	@echo "Running single task locally (TASK_INDEX=$(TASK_INDEX))..."
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id make run-task-local"; \
		exit 1; \
	fi
	@echo "  Reading from: ./local/bucket/$(EXP_ID)/*/builder-artifacts/"
	@echo "  Writing to: ./local/bucket/$(EXP_ID)/*/runner-artifacts/"
	EXP_ID=$(EXP_ID) RUN_ID=$(RUN_ID) TASK_INDEX=$(TASK_INDEX) docker compose run --rm runner
	@echo ""
	@echo "✓ Task $(TASK_INDEX) complete."

run-output-local:
	@echo "Running output generation locally..."
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id NUM_TASKS=10 make run-output-local"; \
		exit 1; \
	fi
	@if [ -z "$(NUM_TASKS)" ]; then \
		echo "ERROR: NUM_TASKS is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id NUM_TASKS=10 make run-output-local"; \
		exit 1; \
	fi
	@echo "  Experiment ID: $(EXP_ID)"
	@if [ -n "$(RUN_ID)" ]; then \
		echo "  Run ID: $(RUN_ID)"; \
	fi
	@echo "  Number of tasks: $(NUM_TASKS)"
	@echo "  Reading from: ./local/bucket/$(EXP_ID)/*/runner-artifacts/"
	@echo "  Writing to: ./local/bucket/$(EXP_ID)/*/outputs/"
	EXP_ID=$(EXP_ID) RUN_ID=$(RUN_ID) NUM_TASKS=$(NUM_TASKS) docker compose run --rm output
	@echo ""
	@echo "✓ Output generation complete. Check ./local/bucket/$(EXP_ID)/*/outputs/ for CSV files."


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
	  -var="github_forecast_repo=$(GITHUB_FORECAST_REPO)" \
	  -var="stage_a_cpu_milli=$(STAGE_A_CPU_MILLI)" \
	  -var="stage_a_memory_mib=$(STAGE_A_MEMORY_MIB)" \
	  -var="stage_a_machine_type=$(STAGE_A_MACHINE_TYPE)" \
	  -var="stage_a_max_run_duration=$(STAGE_A_MAX_RUN_DURATION)" \
	  -var="stage_b_cpu_milli=$(STAGE_B_CPU_MILLI)" \
	  -var="stage_b_memory_mib=$(STAGE_B_MEMORY_MIB)" \
	  -var="stage_b_machine_type=$(STAGE_B_MACHINE_TYPE)" \
	  -var="stage_b_max_run_duration=$(STAGE_B_MAX_RUN_DURATION)" \
	  -var="stage_c_cpu_milli=$(STAGE_C_CPU_MILLI)" \
	  -var="stage_c_memory_mib=$(STAGE_C_MEMORY_MIB)" \
	  -var="stage_c_machine_type=$(STAGE_C_MACHINE_TYPE)" \
	  -var="stage_c_max_run_duration=$(STAGE_C_MAX_RUN_DURATION)" \
	  -var="run_output_stage=$(RUN_OUTPUT_STAGE)" \
	  -var="task_count_per_node=$(TASK_COUNT_PER_NODE)"

tf-apply:
	@echo "Applying Terraform configuration..."
	cd terraform && terraform apply \
	  -var="project_id=$(PROJECT_ID)" \
	  -var="region=$(REGION)" \
	  -var="repo_name=$(REPO_NAME)" \
	  -var="bucket_name=$(BUCKET_NAME)" \
	  -var="image_name=$(IMAGE_NAME)" \
	  -var="image_tag=$(IMAGE_TAG)" \
	  -var="github_forecast_repo=$(GITHUB_FORECAST_REPO)" \
	  -var="stage_a_cpu_milli=$(STAGE_A_CPU_MILLI)" \
	  -var="stage_a_memory_mib=$(STAGE_A_MEMORY_MIB)" \
	  -var="stage_a_machine_type=$(STAGE_A_MACHINE_TYPE)" \
	  -var="stage_a_max_run_duration=$(STAGE_A_MAX_RUN_DURATION)" \
	  -var="stage_b_cpu_milli=$(STAGE_B_CPU_MILLI)" \
	  -var="stage_b_memory_mib=$(STAGE_B_MEMORY_MIB)" \
	  -var="stage_b_machine_type=$(STAGE_B_MACHINE_TYPE)" \
	  -var="stage_b_max_run_duration=$(STAGE_B_MAX_RUN_DURATION)" \
	  -var="stage_c_cpu_milli=$(STAGE_C_CPU_MILLI)" \
	  -var="stage_c_memory_mib=$(STAGE_C_MEMORY_MIB)" \
	  -var="stage_c_machine_type=$(STAGE_C_MACHINE_TYPE)" \
	  -var="stage_c_max_run_duration=$(STAGE_C_MAX_RUN_DURATION)" \
	  -var="run_output_stage=$(RUN_OUTPUT_STAGE)" \
	  -var="task_count_per_node=$(TASK_COUNT_PER_NODE)"

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
	  -var="github_forecast_repo=$(GITHUB_FORECAST_REPO)" \
	  -var="stage_a_cpu_milli=$(STAGE_A_CPU_MILLI)" \
	  -var="stage_a_memory_mib=$(STAGE_A_MEMORY_MIB)" \
	  -var="stage_a_machine_type=$(STAGE_A_MACHINE_TYPE)" \
	  -var="stage_b_cpu_milli=$(STAGE_B_CPU_MILLI)" \
	  -var="stage_b_memory_mib=$(STAGE_B_MEMORY_MIB)" \
	  -var="stage_b_machine_type=$(STAGE_B_MACHINE_TYPE)" \
	  -var="task_count_per_node=$(TASK_COUNT_PER_NODE)"

run-workflow:
	@echo "Submitting workflow (async)..."
	@if [ -z "$(EXP_ID)" ]; then \
		echo "ERROR: EXP_ID is required but not set."; \
		echo "Usage: EXP_ID=your-experiment-id make run-workflow"; \
		exit 1; \
	fi
	@echo "  Experiment ID: $(EXP_ID)"
	@echo "  GitHub Repo: $(GITHUB_FORECAST_REPO)"
	@BATCH_SA=$$(cd terraform && terraform output -raw batch_runtime_sa_email 2>/dev/null || echo "batch-runtime@$(PROJECT_ID).iam.gserviceaccount.com") && \
	curl -X POST \
	  -H "Authorization: Bearer $$(gcloud auth print-access-token)" \
	  -H "Content-Type: application/json" \
	  -d '{"argument":"{\"bucket\":\"$(BUCKET_NAME)\",\"dirPrefix\":\"$(DIR_PREFIX)\",\"exp_id\":\"$(EXP_ID)\",\"githubForecastRepo\":\"$(GITHUB_FORECAST_REPO)\",\"batchSaEmail\":\"'$$BATCH_SA'\"}"}' \
	  "https://workflowexecutions.googleapis.com/v1/projects/$(PROJECT_ID)/locations/$(REGION)/workflows/epymodelingsuite-pipeline/executions" \
	  -s | jq -r '.name' | tee /tmp/workflow_execution.txt && \
	echo "" && \
	echo "✓ Workflow submitted successfully!" && \
	echo "  Execution: $$(cat /tmp/workflow_execution.txt)" && \
	echo "" && \
	echo "Monitor with:" && \
	echo "  gcloud workflows executions describe $$(basename $$(cat /tmp/workflow_execution.txt)) --workflow=epymodelingsuite-pipeline --location=$(REGION)" && \
	echo "  gcloud workflows executions list epymodelingsuite-pipeline --location=$(REGION)"

clean:
	@echo "Cleaning local artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"
