# epycloud terraform

Manage Google Cloud infrastructure with Terraform.

## Usage

```bash
epycloud terraform SUBCOMMAND [OPTIONS]
epycloud tf SUBCOMMAND [OPTIONS]  # Short alias
```

## Description

Manages Google Cloud infrastructure resources using Terraform. Provides a wrapper around Terraform commands with environment-aware configuration and safety checks. Commands automatically use the appropriate Terraform workspace and variable files based on the active environment.

## Subcommands

### init

Initialize Terraform working directory.

```bash
epycloud terraform init
```

Downloads providers, configures remote backend (GCS), and prepares directory.

### plan

Preview infrastructure changes without applying.

```bash
epycloud terraform plan [OPTIONS]
```

**Options:**
- `--target RESOURCE` - Plan changes for specific resource only
- `--out FILE` - Save plan to file

### apply

Apply infrastructure changes.

```bash
epycloud terraform apply [OPTIONS]
```

**Options:**
- `--auto-approve` - Skip interactive approval prompt
- `--target RESOURCE` - Apply changes to specific resource only

### destroy

Destroy all managed infrastructure.

```bash
epycloud terraform destroy [OPTIONS]
```

**Options:**
- `--auto-approve` - Skip interactive approval prompt
- `--target RESOURCE` - Destroy specific resource only

!!! danger "Destructive Operation"
    This permanently deletes cloud resources and data. Always verify environment before destroying.

### output

Display Terraform output values.

```bash
epycloud terraform output [NAME]
```

## Examples

```bash
# Initialize Terraform
epycloud tf init

# Preview changes
epycloud tf plan

# Apply changes
epycloud tf apply

# Apply without confirmation
epycloud tf apply --auto-approve

# Apply to production
epycloud --env prod tf apply

# Apply specific resource
epycloud tf apply --target google_workflows_workflow.pipeline

# Show all outputs
epycloud tf output

# Show specific output
epycloud tf output bucket_name

# Destroy all resources
epycloud tf destroy

# Destroy dev environment
epycloud --env dev tf destroy
```

## Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Error (validation failed, apply failed) |
| `2` | Plan shows changes (with `-detailed-exitcode`) |

## Related Commands

- [`epycloud config`](config.md) - Configure project and environment settings

## See Also

- [Cloud Deployment](../getting-started/cloud-deployment/index.md) - Setup and deployment guide
