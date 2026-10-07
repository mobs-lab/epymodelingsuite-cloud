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
## Blue/green staging pipeline

Two workflows are deployed from one state:

| Workflow | Rendered from | Selected with |
|---|---|---|
| `epymodelingsuite-pipeline` | `workflow.yaml` | default (no `--env`) |
| `epymodelingsuite-pipeline-staging` | `workflow-staging.yaml` + `workflow-staging-subworkflows.yaml` | `epycloud --env staging ...` |

It is called `staging`, not `dev`, because "dev" is already
taken in this project by the dev git branch, the `dev` image tag and
`github.modeling_suite_ref: dev`. Those select which *code* runs; this selects which
*workflow* runs, which is a separate axis. `--env dev` still exists for the first kind.

The staging source is split at the top-level subworkflow boundary. `workflow-staging.yaml`
contains `main`; `workflow-staging-subworkflows.yaml` contains the reusable subworkflows.
Terraform joins them into one definition. Editing either and applying changes **only**
the staging workflow. Everything else (network, subnet, Artifact Registry, both service
accounts) is shared; a workflow only reads those, and Batch jobs hold no shared state.

The three stage loops keep their stage-specific Batch job bodies explicit. Their shared
post-submission lifecycle lives in `waitAndFinalizeCandidate`, which owns completion
waiting, manual-child-cancellation handling, cancellation and draining, terminal-state
races, and candidate exhaustion. Keep those semantics in the subworkflow so the three
stages cannot drift apart.

Workflow changes therefore go: edit the staging templates, apply, exercise with
`--env staging`, then promote the assembled definition.

```bash
# Promote a validated staging workflow to production
{ cat terraform/workflow-staging.yaml; printf '\n'; cat terraform/workflow-staging-subworkflows.yaml; } > /tmp/workflow-staging-assembled.yaml
diff terraform/workflow.yaml /tmp/workflow-staging-assembled.yaml
cp /tmp/workflow-staging-assembled.yaml terraform/workflow.yaml
epycloud terraform apply
```

Set `enable_staging_workflow = false` to tear the staging workflow down without removing the code.

### Run terraform from the base environment, not `--env staging`

`var.workflow_name` is the **production** name; the staging workflow is derived as
`"${var.workflow_name}-staging"`. Because `epycloud` exports config as `TF_VAR_*`, running
`epycloud --env staging terraform apply` would pass the already-suffixed staging name and
rename the production workflow. An HCL validation rejects any `workflow_name` ending in
`-staging`, so this fails fast instead of destroying and recreating the production workflow.
