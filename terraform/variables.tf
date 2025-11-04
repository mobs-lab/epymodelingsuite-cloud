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
  default     = "epymodelingsuite-repo"
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

# Batch machine configuration - Stage A (Dispatcher)
variable "stage_a_cpu_milli" {
  type        = number
  default     = 2000
  description = "CPU allocation for Stage A in milli-cores (1000 = 1 vCPU)"
}

variable "stage_a_memory_mib" {
  type        = number
  default     = 4096
  description = "Memory allocation for Stage A in MiB"
}

variable "stage_a_machine_type" {
  type        = string
  default     = ""
  description = "Machine type for Stage A (optional, e.g., 'e2-standard-2'). Empty string = auto-select"
}

variable "stage_a_max_run_duration" {
  type        = number
  default     = 3600
  description = "Maximum runtime for Stage A in seconds (default: 3600s = 1 hour)"
}

# Batch machine configuration - Stage B (Runner)
variable "stage_b_cpu_milli" {
  type        = number
  default     = 2000
  description = "CPU allocation for Stage B in milli-cores (1000 = 1 vCPU)"
}

variable "stage_b_memory_mib" {
  type        = number
  default     = 4096
  description = "Memory allocation for Stage B in MiB"
}

variable "stage_b_machine_type" {
  type        = string
  default     = ""
  description = "Machine type for Stage B (optional, e.g., 'n2-standard-4'). Empty string = auto-select"
}

variable "stage_b_max_run_duration" {
  type        = number
  default     = 36000
  description = "Maximum runtime for Stage B tasks in seconds (default: 36000s = 10 hours)"
}

variable "task_count_per_node" {
  type        = number
  default     = 1
  description = "Maximum tasks per VM (1 = dedicated VM per task, 2+ = shared VMs)"
}

# Batch machine configuration - Stage C (Output)
variable "stage_c_cpu_milli" {
  type        = number
  default     = 2000
  description = "CPU allocation for Stage C in milli-cores (1000 = 1 vCPU)"
}

variable "stage_c_memory_mib" {
  type        = number
  default     = 8192
  description = "Memory allocation for Stage C in MiB"
}

variable "stage_c_machine_type" {
  type        = string
  default     = ""
  description = "Machine type for Stage C (optional, e.g., 'e2-standard-2'). Empty string = auto-select"
}

variable "stage_c_max_run_duration" {
  type        = number
  default     = 7200
  description = "Maximum runtime for Stage C in seconds (default: 7200s = 2 hours)"
}

variable "run_output_stage" {
  type        = bool
  default     = true
  description = "Whether to run Stage C (Output generation). Set to false to skip output generation."
}

# Network configuration
variable "network_name" {
  type        = string
  default     = "epymodelingsuite-network"
  description = "VPC network name for Cloud Batch"
}

variable "subnet_name" {
  type        = string
  default     = "epymodelingsuite-subnet"
  description = "Subnet name for Cloud Batch"
}

variable "subnet_cidr" {
  type        = string
  default     = "10.0.0.0/20"
  description = "CIDR range for subnet (10.0.0.0/20 = 4096 IPs)"
}
