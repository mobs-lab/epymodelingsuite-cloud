# VPC Network for Cloud Batch
resource "google_compute_network" "batch_network" {
  name                    = var.network_name
  auto_create_subnetworks = false
  description             = "VPC network for epymodelingsuite Cloud Batch jobs"
}

# Subnet with Private Google Access
resource "google_compute_subnetwork" "batch_subnet" {
  for_each = var.batch_regions

  name          = each.key == var.region ? var.subnet_name : "${var.subnet_name}-${each.key}"
  ip_cidr_range = each.value.subnet_cidr
  region        = each.key
  network       = google_compute_network.batch_network.id
  description = each.key == var.region ? (
    "Subnet for Cloud Batch with Private Google Access"
  ) : "Subnet for Cloud Batch in ${each.key} with Private Google Access"

  # Enable Private Google Access for GCS, Artifact Registry, Secret Manager
  private_ip_google_access = true
}

# Cloud Router for Cloud NAT
resource "google_compute_router" "batch_router" {
  for_each = var.batch_regions

  name    = each.key == var.region ? "${var.network_name}-router" : "${var.network_name}-router-${each.key}"
  region  = each.key
  network = google_compute_network.batch_network.id

  description = each.key == var.region ? (
    "Router for Cloud NAT to enable outbound internet access"
  ) : "Router for Cloud NAT in ${each.key}"
}

# Cloud NAT for outbound internet access (GitHub cloning, etc.)
resource "google_compute_router_nat" "batch_nat" {
  for_each = var.batch_regions

  name   = each.key == var.region ? "${var.network_name}-nat" : "${var.network_name}-nat-${each.key}"
  router = google_compute_router.batch_router[each.key].name
  region = each.key

  # Auto-allocate NAT IPs
  nat_ip_allocate_option = "AUTO_ONLY"

  # Apply to all subnets in the region
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  # Dynamic port allocation to handle many concurrent VMs
  # min=1024 ensures enough ports for GitHub cloning + GCS operations
  enable_dynamic_port_allocation = true
  min_ports_per_vm               = 1024
  max_ports_per_vm               = 4096

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

check "default_batch_region_configured" {
  assert {
    condition     = contains(keys(var.batch_regions), var.region)
    error_message = "batch_regions must contain the control-plane region from var.region."
  }
}

moved {
  from = google_compute_subnetwork.batch_subnet
  to   = google_compute_subnetwork.batch_subnet["us-central1"]
}

moved {
  from = google_compute_router.batch_router
  to   = google_compute_router.batch_router["us-central1"]
}

moved {
  from = google_compute_router_nat.batch_nat
  to   = google_compute_router_nat.batch_nat["us-central1"]
}
