variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Google Cloud region for control-plane resources"
}

variable "batch_regions" {
  type = map(object({
    subnet_cidr = string
  }))
  description = "Data-plane regions and their Cloud Batch subnet CIDR ranges"
  default = {
    us-central1 = { subnet_cidr = "10.0.0.0/20" }
    us-east5    = { subnet_cidr = "10.1.0.0/20" }
  }

  validation {
    condition = length(var.batch_regions) > 0 && alltrue([
      for region, config in var.batch_regions :
      region != "" && can(cidrhost(config.subnet_cidr, 0))
    ])
    error_message = "batch_regions must contain at least one non-empty region with a valid subnet_cidr."
  }

  validation {
    condition = length(distinct([
      for config in values(var.batch_regions) : config.subnet_cidr
    ])) == length(var.batch_regions)
    error_message = "Each batch region must use a distinct subnet_cidr."
  }
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

variable "workflow_name" {
  type        = string
  default     = "epymodelingsuite-pipeline"
  description = "Name of the production Cloud Workflows workflow. The staging workflow is always this name suffixed with '-staging'."

  validation {
    condition     = !endswith(var.workflow_name, "-staging")
    error_message = "workflow_name is the PRODUCTION workflow name; the staging workflow is derived as \"$${var.workflow_name}-staging\". A '-staging' suffix here means terraform was run under the staging environment (e.g. 'epycloud --env staging terraform apply'), which would rename the production workflow. Run terraform without --env staging."
  }
}

variable "enable_staging_workflow" {
  type        = bool
  default     = true
  description = "Deploy the blue/green staging workflow assembled from its main and subworkflow templates. Set false to tear it down."
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
  default     = 8192
  description = "Memory allocation for Stage A in MiB"
}

variable "stage_a_machine_type" {
  type        = string
  default     = "c4d-standard-2"
  description = "Machine type for Stage A. Must be Hyperdisk-capable (c3, c3d, c4, c4d, n4, n4d), e.g. 'c4d-standard-2'. Empty string = auto-select"

  # C4/C4D/N4/N4D are Hyperdisk-only and the workflow emits a hyperdisk-balanced
  # bootDisk for any non-empty machine type. A family that cannot boot from it
  # renders a workflow that Batch accepts and then fails ~1080s later at VM
  # creation, blaming the disk type. Mirrors is_hyperdisk_family() in
  # src/epycloud/execution/gcp_machines.py. Keep the two lists in step.
  validation {
    condition     = var.stage_a_machine_type == "" || contains(["c3", "c3d", "c4", "c4d", "n4", "n4d"], split("-", var.stage_a_machine_type)[0])
    error_message = "Stage A machine type must be empty (auto-select) or in a Hyperdisk-capable family: c3, c3d, c4, c4d, n4, n4d. This pipeline boots VMs with bootDisk type 'hyperdisk-balanced'; other families are accepted by Batch and then fail at VM creation."
  }
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
  description = "Machine type for Stage B. Must be Hyperdisk-capable (c3, c3d, c4, c4d, n4, n4d), e.g. 'c4d-standard-2'. Empty string = auto-select"

  # C4/C4D/N4/N4D are Hyperdisk-only and the workflow emits a hyperdisk-balanced
  # bootDisk for any non-empty machine type. A family that cannot boot from it
  # renders a workflow that Batch accepts and then fails ~1080s later at VM
  # creation, blaming the disk type. Mirrors is_hyperdisk_family() in
  # src/epycloud/execution/gcp_machines.py. Keep the two lists in step.
  validation {
    condition     = var.stage_b_machine_type == "" || contains(["c3", "c3d", "c4", "c4d", "n4", "n4d"], split("-", var.stage_b_machine_type)[0])
    error_message = "Stage B machine type must be empty (auto-select) or in a Hyperdisk-capable family: c3, c3d, c4, c4d, n4, n4d. This pipeline boots VMs with bootDisk type 'hyperdisk-balanced'; other families are accepted by Batch and then fail at VM creation."
  }
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
  default     = 4000
  description = "CPU allocation for Stage C in milli-cores (1000 = 1 vCPU)"
}

variable "stage_c_memory_mib" {
  type        = number
  default     = 15360
  description = "Memory allocation for Stage C in MiB"
}

variable "stage_c_machine_type" {
  type        = string
  default     = "c4d-standard-4"
  description = "Machine type for Stage C. Must be Hyperdisk-capable (c3, c3d, c4, c4d, n4, n4d), e.g. 'c4d-standard-4'. Empty string = auto-select"

  # C4/C4D/N4/N4D are Hyperdisk-only and the workflow emits a hyperdisk-balanced
  # bootDisk for any non-empty machine type. A family that cannot boot from it
  # renders a workflow that Batch accepts and then fails ~1080s later at VM
  # creation, blaming the disk type. Mirrors is_hyperdisk_family() in
  # src/epycloud/execution/gcp_machines.py. Keep the two lists in step.
  validation {
    condition     = var.stage_c_machine_type == "" || contains(["c3", "c3d", "c4", "c4d", "n4", "n4d"], split("-", var.stage_c_machine_type)[0])
    error_message = "Stage C machine type must be empty (auto-select) or in a Hyperdisk-capable family: c3, c3d, c4, c4d, n4, n4d. This pipeline boots VMs with bootDisk type 'hyperdisk-balanced'; other families are accepted by Batch and then fail at VM creation."
  }
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
  description = "Deprecated. Configure per-region CIDRs with batch_regions."
}
