# Machine Types

Google Cloud offers different machine types that vary in CPU architecture, memory, and price. Cloud Batch provisions VMs of the chosen machine type to run each pipeline task.

For how cpuMilli and memoryMib map to machine resources, see [Cloud Batch: Resource units](cloud-batch.md#resource-units). For recommended configurations per stage, see [Sizing Recommendations](sizing-recommendations.md).

## Machine family overview

A machine family groups machine types that share the same CPU platform and pricing model. The pipeline primarily uses **C4D** (AMD compute-optimized) for its strong single-thread performance at a competitive price, but other families are available depending on your workload.

Here are some examples of machine families that can fit your needs:

| Family | Best for | CPU | Characteristics |
|--------|----------|-----|-----------------|
| **E2** | Cost-sensitive workloads | Variable | Lowest cost, shared-core available, variable CPU performance |
| **N2** | General workloads | Intel Cascade Lake / Ice Lake | Good balance of price and performance |
| **C4** | Compute-intensive | Intel Sapphire Rapids | Latest Intel, high single-thread performance |
| **C4D** | Compute-intensive | AMD EPYC Genoa | Latest AMD, excellent single-thread performance, slightly lower cost than C4 |

For details on each machine families and pricing, see:

<!-- link-card: https://docs.cloud.google.com/compute/docs/machine-resource#recommendations_for_machine_types
    | title="Machine families resource and comparison guide | Google Cloud"
    | description=false
-->

<!-- link-card: https://cloud.google.com/compute/vm-instance-pricing?hl=en#general-purpose-machine-type-family
    | title="VM instance pricing | Google Cloud"
    | description=false
-->


## Machine type selection

### How it works

When Cloud Batch runs a job, it provisions VMs to execute tasks. There are two approaches to control which VMs get provisioned:

**Auto-select**: Specify only [CPU and memory requirements](cloud-batch.md#resource-units). Cloud Batch picks a machine type that satisfies them. This is simpler but less predictable, as Google may choose slower machine families (e.g., E2) when requirements are low.

**Explicit machine type**: Specify the exact machine type (e.g., `c4d-standard-2`). Cloud Batch provisions that specific VM. The CPU and memory values become task-level constraints and must not exceed the machine's capacity. If the values are smaller than the machine's capacity, Cloud Batch may pack multiple tasks onto the same VM (controlled by `task_count_per_node`). This gives predictable provisioning and consistent performance.

!!! tip
    For production workloads, we recommend setting an explicit `machine_type` with `task_count_per_node: 1`. This gives each task a dedicated VM and ensures predictable scaling.

For details on how Batch automatically creates and deltes resources that meet specification, see:

<!-- link-card: https://docs.cloud.google.com/batch/docs/create-run-job#resources
    | title="Job resources | Cloud Batch | Google Cloud"
    | description=false
"
 -->

### Pipeline configuration

In the pipeline, machine type selection is configured per stage:

=== "Auto-select"

    ```yaml
    google_cloud:
      batch:
        stage_b:
          cpu_milli: 2000
          memory_mib: 4096
          machine_type: ""  # Cloud Batch picks the VM
    ```

=== "Explicit machine type"

    ```yaml
    google_cloud:
      batch:
        stage_b:
          cpu_milli: 2000
          memory_mib: 7168
          machine_type: "c4d-standard-2"
    ```

See [Configuration Variables](../configuration-variables.md#google_cloudbatch) for all per-stage resource settings.

## Naming convention

Google Cloud machine types follow the pattern: `{family}-{type}-{vcpus}`

- **Family**: `e2`, `n2`, `c4`, `c4d`, etc.
- **Type**: `standard` (balanced), `highmem` (more memory per vCPU), `highcpu` (more vCPUs per memory)
- **vCPUs**: Number of virtual CPUs (2, 4, 8, 16, ...)

Examples:

- `c4d-standard-2`: C4D family, standard memory, 2 vCPUs
- `c4d-highmem-4`: C4D family, high memory, 4 vCPUs
- `e2-standard-4`: E2 family, standard memory, 4 vCPUs

For full list of machine types, see:
<!-- link-card: https://cloud.google.com/compute/vm-instance-pricing?hl=en#general-purpose-machine-type-family
    | title="VM instance pricing | Google Cloud"
    | description=false
-->

## Common machine types

Machine types commonly used by the pipeline. A typical calibration task in Stage B for a single state uses approximately 4 GB of memory. For per-stage defaults and guidance, see [Sizing Recommendations](sizing-recommendations.md).

### 2-vCPU machine types

| Machine Type | vCPU | Memory | Price (us-central1) | CPU | Notes |
|--------------|------|--------|---------------------|-----|-------|
| `e2-standard-2` | 2 | 8 GB | $0.067/hr | Variable | Most cost-effective, general purpose |
| `n2-standard-2` | 2 | 8 GB | $0.097/hr | Intel Cascade Lake / Ice Lake | Better CPU performance than E2 |
| `c4-standard-2` | 2 | 8 GB | $0.097/hr | Intel Sapphire Rapids | Intel compute-optimized |
| `c4d-standard-2` | 2 | 7 GB | $0.090/hr | AMD EPYC Genoa | AMD compute-optimized |
| `c4d-highmem-2` | 2 | 15 GB | $0.118/hr | AMD EPYC Genoa | High memory + compute |

### 4-vCPU machine types

Use these for memory-intensive workloads such as Stage C (output aggregation), which loads all Stage B results into memory.

| Machine Type | vCPU | Memory | Price (us-central1) | CPU | Notes |
|--------------|------|--------|---------------------|-----|-------|
| `e2-standard-4` | 4 | 16 GB | $0.134/hr | Variable | Cost-effective |
| `n2-standard-4` | 4 | 16 GB | $0.194/hr | Intel Cascade Lake / Ice Lake | Balanced performance |
| `c4-standard-4` | 4 | 16 GB | $0.198/hr | Intel Sapphire Rapids | Intel compute-optimized |
| `c4d-standard-4` | 4 | 15 GB | $0.183/hr | AMD EPYC Genoa | AMD compute-optimized |
| `c4d-highmem-4` | 4 | 31 GB | $0.239/hr | AMD EPYC Genoa | High memory + compute |

!!! note
    Prices are approximate on-demand rates for `us-central1` as of October 2025. See [Google Cloud VM pricing](https://cloud.google.com/compute/vm-instance-pricing) for current rates and [machine type documentation](https://cloud.google.com/compute/docs/general-purpose-machines) for full specifications.

For Cloud Build machine types, see [Cloud Build](cloud-build.md#machine-types).
