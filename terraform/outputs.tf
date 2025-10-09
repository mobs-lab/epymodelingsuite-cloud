output "artifact_registry_repo" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repo_name}"
  description = "Full path to Artifact Registry repository"
}

output "bucket_name" {
  value       = var.bucket_name
  description = "GCS bucket name"
}

output "workflows_name" {
  value       = google_workflows_workflow.pipeline.name
  description = "Workflows workflow name"
}

output "workflows_region" {
  value       = var.region
  description = "Workflows region"
}

output "batch_runtime_sa_email" {
  value       = google_service_account.batch_runtime.email
  description = "Batch runtime service account email"
}

output "workflows_runner_sa_email" {
  value       = google_service_account.workflows_runner.email
  description = "Workflows runner service account email"
}

output "image_uri" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repo_name}/${var.image_name}:${var.image_tag}"
  description = "Full Docker image URI"
}
