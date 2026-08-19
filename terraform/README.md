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
  - `google_cloud.workflow_name`: Cloud Workflows workflow to deploy and submit to (default: `epymodelingsuite-pipeline`)

See [docs/variable-configuration.md](../docs/variable-configuration.md) for complete configuration reference.

## Blue/green dev pipeline

Two workflows are deployed from one state:

| Workflow | Rendered from | Selected with |
|---|---|---|
| `epymodelingsuite-pipeline` | `workflow.yaml` | default (no `--env`) |
| `epymodelingsuite-pipeline-dev` | `workflow-dev.yaml` | `epycloud --env dev ...` |

`workflow-dev.yaml` starts as a byte-identical copy of `workflow.yaml`. Editing it and
applying changes **only** the dev workflow — the isolation is structural, so there is no
`-target` flag to remember. Everything else (network, subnet, Artifact Registry, both
service accounts) is shared; a workflow only reads those, and Batch jobs hold no shared
state.

Workflow changes therefore go: edit `workflow-dev.yaml` → apply → exercise with
`--env dev` → promote.

```bash
# Promote a validated dev workflow to production
diff terraform/workflow.yaml terraform/workflow-dev.yaml   # review before promoting
cp terraform/workflow-dev.yaml terraform/workflow.yaml
epycloud terraform apply
```

Set `enable_dev_workflow = false` to tear the dev workflow down without removing the code.

### Run terraform from the base environment, not `--env dev`

`var.workflow_name` is the **production** name; the dev workflow is derived as
`"${var.workflow_name}-dev"`. Because `epycloud` exports config as `TF_VAR_*`, running
`epycloud --env dev terraform apply` would pass the already-suffixed dev name and rename
the production workflow. An HCL validation rejects any `workflow_name` ending in `-dev`,
so this fails fast instead of destroying and recreating the production workflow.
