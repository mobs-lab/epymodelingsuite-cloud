variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Google Cloud region for resources"
}

variable "repo_name" {
  type        = string
  default     = "epydemix"
  description = "Artifact Registry repository name"
}

variable "bucket_name" {
  type        = string
  description = "GCS bucket name for data storage"
}

variable "image_name" {
  type        = string
  default     = "epymodelingsuite"
  description = "Docker image name"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Docker image tag"
}

variable "github_forecast_repo" {
  type        = string
  description = "Private GitHub repository for forecast (format: username/reponame)"
}
