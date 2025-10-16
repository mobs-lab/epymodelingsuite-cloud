# Terraform Configuration

## Configuration Management

**This project uses `.env` as the single source of truth for all configuration.**

### DO NOT use `terraform.tfvars`

The Makefile reads configuration from `.env` (in the project root) and passes values to Terraform via `-var` flags. This ensures:
- Single source of truth across Make, Docker, and Terraform
- No duplicate configuration files
- Consistent behavior across all tools

### How to Configure

1. Copy `.env.example` to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   vim .env  # or your preferred editor
   ```

3. Source and apply:
   ```bash
   source .env
   make tf-apply
   ```

### Available Configuration

See [.env.example](../.env.example) for all available configuration options, including:

- Google Cloud infrastructure (project, region, bucket)
- Docker image configuration
- GitHub repositories
- **Batch machine configuration** (CPU, memory, machine type)
  - Stage A (Dispatcher): `STAGE_A_CPU_MILLI`, `STAGE_A_MEMORY_MIB`, `STAGE_A_MACHINE_TYPE`
  - Stage B (Runner): `STAGE_B_CPU_MILLI`, `STAGE_B_MEMORY_MIB`, `STAGE_B_MACHINE_TYPE`

### Why Not terraform.tfvars?

While `terraform.tfvars` is the standard Terraform way to set variables, our Makefile-based workflow overrides it completely. Using `.env` provides:
- Works with Make, docker-compose, and shell scripts
- Single file to maintain
- No confusion about which config file is active
