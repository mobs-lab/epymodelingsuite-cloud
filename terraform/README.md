# Terraform Configuration

## Configuration Management

**This project uses the unified configuration system (`config.yaml`) for all configuration.**

### Configuration System

The `epycloud` CLI manages configuration and passes values to Terraform automatically. Configuration is stored in `~/.config/epymodelingsuite-cloud/config.yaml`.

This ensures:
- Single source of truth across CLI, Docker, and Terraform
- No duplicate configuration files
- Consistent behavior across all tools
- Secure secrets management

### How to Configure

1. Initialize configuration:
   ```bash
   epycloud config init
   ```

2. Edit configuration:
   ```bash
   epycloud config edit          # Edit base configuration
   epycloud config edit-secrets  # Edit secrets (GitHub PAT)
   ```

3. Verify and apply:
   ```bash
   epycloud config show         # Verify configuration
   epycloud terraform apply     # Deploy infrastructure
   ```

### Available Configuration

Configuration is stored in YAML format with hierarchical structure. Key sections include:

- **Google Cloud infrastructure** (`google_cloud.project_id`, `region`, `bucket_name`)
- **Docker image configuration** (`docker.repo_name`, `image_name`, `image_tag`)
- **GitHub repositories** (`github.forecast_repo`, `modeling_suite_repo`)
- **Batch machine configuration** (Cloud Batch resources)
  - Stage A (Builder): `google_cloud.batch.stage_a` (cpu_milli, memory_mib, machine_type)
  - Stage B (Runner): `google_cloud.batch.stage_b` (cpu_milli, memory_mib, machine_type, max_run_duration)
  - Stage C (Output): `google_cloud.batch.stage_c` (cpu_milli, memory_mib, machine_type, max_run_duration)
- **Pipeline control**
  - `google_cloud.batch.run_output_stage`: Enable/disable Stage C output generation (default: `true`)

See [docs/variable-configuration.md](../docs/variable-configuration.md) for complete configuration reference.
