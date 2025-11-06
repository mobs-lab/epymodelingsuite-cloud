terraform {
  required_version = ">= 1.5.0"

  backend "gcs" {
    bucket = "gs_mobs_jessica"
    prefix = "pipeline-terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "batch" {
  service            = "batch.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "workflows" {
  service            = "workflows.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry (Docker)
resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.repo_name
  format        = "DOCKER"
  description   = "Docker repository for epymodelingsuite pipeline"

  labels = {
    component   = "epymodelingsuite"
    project     = "epymodelingsuite-cloud"
    environment = "production"
    managed-by  = "terraform"
  }

  depends_on = [google_project_service.artifactregistry]
}

# Use existing GCS bucket
data "google_storage_bucket" "data" {
  name = var.bucket_name
}

# Secret Manager: GitHub Fine-Grained Personal Access Token
# Note: The actual secret value must be created manually via:
# echo -n "your_pat_here" | gcloud secrets create github-pat --data-file=-
# Required permissions: Contents (read) for epymodelingsuite and forecasting repositories
resource "google_secret_manager_secret" "github_pat" {
  secret_id = "github-pat"

  labels = {
    component   = "epymodelingsuite"
    project     = "epymodelingsuite-cloud"
    environment = "production"
    managed-by  = "terraform"
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# Service Account for Batch runtime
resource "google_service_account" "batch_runtime" {
  account_id   = "batch-runtime"
  display_name = "Batch Runtime SA"
  description  = "Service account for Cloud Batch jobs"
}

# Service Account for Workflows
resource "google_service_account" "workflows_runner" {
  account_id   = "workflows-runner"
  display_name = "Workflows Runner SA"
  description  = "Service account for Workflows orchestration"
}

# IAM: Batch runtime needs GCS write/read
resource "google_storage_bucket_iam_member" "batch_sa_bucket_rw" {
  bucket = data.google_storage_bucket.data.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.batch_runtime.email}"
}

# IAM: Batch runtime needs to write logs
resource "google_project_iam_member" "batch_sa_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.batch_runtime.email}"
}

# IAM: Batch runtime needs to pull Docker images from Artifact Registry
resource "google_project_iam_member" "batch_sa_artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.batch_runtime.email}"
}

# IAM: Batch runtime needs to report task status to Batch API
resource "google_project_iam_member" "batch_sa_agent_reporter" {
  project = var.project_id
  role    = "roles/batch.agentReporter"
  member  = "serviceAccount:${google_service_account.batch_runtime.email}"
}

# IAM: Batch runtime needs to access GitHub PAT from Secret Manager
resource "google_secret_manager_secret_iam_member" "batch_sa_secret_accessor" {
  secret_id = google_secret_manager_secret.github_pat.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.batch_runtime.email}"
}

# Workflows runner: manage Batch jobs
resource "google_project_iam_member" "wf_batch_admin" {
  project = var.project_id
  role    = "roles/batch.jobsAdmin"
  member  = "serviceAccount:${google_service_account.workflows_runner.email}"

  depends_on = [google_project_service.batch]
}

# Workflows runner: impersonate Batch service account specifically
resource "google_service_account_iam_member" "wf_impersonate_batch" {
  service_account_id = google_service_account.batch_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.workflows_runner.email}"
}

# Additional: Grant Service Account User at project level
# Some GCP services require both project and resource-level permissions
resource "google_project_iam_member" "wf_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.workflows_runner.email}"
}

# Workflows runner: read bucket objects to count N
resource "google_storage_bucket_iam_member" "wf_bucket_view" {
  bucket = data.google_storage_bucket.data.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.workflows_runner.email}"
}

# Workflows runner: write logs
resource "google_project_iam_member" "wf_logs_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.workflows_runner.email}"
}

# Wait for Workflows service agent to be created
# The service agent is created automatically when the API is enabled,
# but there's a delay before it's ready
resource "time_sleep" "wait_for_workflows_agent" {
  depends_on = [google_project_service.workflows]

  create_duration = "60s"
}

# Get project number for Workflows service agent
data "google_project" "project" {
  project_id = var.project_id
}

# Allow Workflows service agent to act as the workflows-runner service account
# This is required for Workflows to use the custom service account
resource "google_service_account_iam_member" "workflows_agent_use_runner" {
  service_account_id = google_service_account.workflows_runner.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-workflows.iam.gserviceaccount.com"
}

# Workflows (deploy from local YAML with variable substitution)
resource "google_workflows_workflow" "pipeline" {
  name            = "epymodelingsuite-pipeline"
  description     = "Stage A (gen) → list GCS → Stage B (array) → Stage C (output)"
  region          = var.region
  service_account = google_service_account.workflows_runner.email
  source_contents = templatefile("${path.module}/workflow.yaml", {
    repo_name           = var.repo_name
    image_name          = var.image_name
    image_tag           = var.image_tag
    stage_a_cpu_milli   = var.stage_a_cpu_milli
    stage_a_memory_mib  = var.stage_a_memory_mib
    stage_a_machine_type = var.stage_a_machine_type
    stage_a_max_run_duration = var.stage_a_max_run_duration
    stage_b_cpu_milli   = var.stage_b_cpu_milli
    stage_b_memory_mib  = var.stage_b_memory_mib
    stage_b_machine_type = var.stage_b_machine_type
    stage_b_max_run_duration = var.stage_b_max_run_duration
    stage_c_cpu_milli   = var.stage_c_cpu_milli
    stage_c_memory_mib  = var.stage_c_memory_mib
    stage_c_machine_type = var.stage_c_machine_type
    stage_c_max_run_duration = var.stage_c_max_run_duration
    task_count_per_node = var.task_count_per_node
    run_output_stage    = var.run_output_stage
    network_name        = google_compute_network.batch_network.name
    subnet_name         = google_compute_subnetwork.batch_subnet.name
    subnet_self_link    = google_compute_subnetwork.batch_subnet.self_link
  })

  labels = {
    component   = "epymodelingsuite"
    project     = "epymodelingsuite-cloud"
    environment = "production"
    managed-by  = "terraform"
  }

  depends_on = [
    google_project_service.workflows,
    time_sleep.wait_for_workflows_agent,
    google_service_account_iam_member.workflows_agent_use_runner
  ]
}
