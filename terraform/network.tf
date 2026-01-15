# VPC Network for Cloud Batch
resource "google_compute_network" "batch_network" {
  name                    = var.network_name
  auto_create_subnetworks = false
  description             = "VPC network for epymodelingsuite Cloud Batch jobs"
}

# Subnet with Private Google Access
resource "google_compute_subnetwork" "batch_subnet" {
  name          = var.subnet_name
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.batch_network.id
  description   = "Subnet for Cloud Batch with Private Google Access"

  # Enable Private Google Access for GCS, Artifact Registry, Secret Manager
  private_ip_google_access = true
}

# Cloud Router for Cloud NAT
resource "google_compute_router" "batch_router" {
  name    = "${var.network_name}-router"
  region  = var.region
  network = google_compute_network.batch_network.id

  description = "Router for Cloud NAT to enable outbound internet access"
}

# Cloud NAT for outbound internet access (GitHub cloning, etc.)
resource "google_compute_router_nat" "batch_nat" {
  name   = "${var.network_name}-nat"
  router = google_compute_router.batch_router.name
  region = var.region

  # Auto-allocate NAT IPs
  nat_ip_allocate_option = "AUTO_ONLY"

  # Apply to all subnets in the region
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  # Dynamic port allocation to handle many concurrent VMs
  enable_dynamic_port_allocation = true
  min_ports_per_vm               = 64
  max_ports_per_vm               = 4096

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
