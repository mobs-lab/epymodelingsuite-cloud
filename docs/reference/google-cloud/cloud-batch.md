# Cloud Batch

Google Cloud Batch is a serverless compute service that provisions VMs and runs containers. The pipeline uses Cloud Batch to execute all stages.

<!-- 
link-card: https://docs.cloud.google.com/batch/docs
    | title="Batch documentation | Compute Engine | Google Cloud"
    | description=false
-->


## Jobs and tasks

A **Batch job** is a unit of work you submit to Cloud Batch. Each job specifies a container image, resource requirements, and one or more **tasks** to run. Tasks within a job run independently, each in its own container.

Every task is assigned a zero-based **task index** (`BATCH_TASK_INDEX`) that the pipeline uses to determine which input file to process (e.g., task 0 reads `input_0000.pkl`, task 5 reads `input_0005.pkl`).

| | Stage A (Builder) | Stage B (Runner) | Stage C (Output) |
|---|---|---|---|
| **Tasks** | 1 | N (one per input file) | 1 |
| **Purpose** | Generate N input files | Process inputs in parallel | Aggregate all results |

A job progresses through these states: **QUEUED** → **SCHEDULED** → **RUNNING** → **SUCCEEDED** or **FAILED**.

For more details on Batch components:
<!-- 
link-card: https://docs.cloud.google.com/batch/docs/get-started#product-overview
    | title="Get started with Batch | Google Cloud"
    | description=false
-->


## Parallelism

**Parallelism** controls how many tasks run at the same time within a job. If a job has 1,000 tasks and parallelism is set to 100, Cloud Batch runs up to 100 tasks concurrently and queues the rest.

| Setting | Value |
|---------|-------|
| Default | 100 |
| Cloud Batch maximum | 5,000 per job |
| Configuration key | `google_cloud.batch.max_parallelism` |

For more details on parallelism:

<!-- 
link-card: https://docs.cloud.google.com/batch/docs/create-run-job#execution
    | title="Job creation and execution overview | Google Cloud"
    | description=false
-->


## Resource units

Cloud Batch uses two units to express compute requirements per task: cpuMilli and memoryMib. These values are set per stage in configuration (e.g., `google_cloud.batch.stage_b.cpu_milli`). See [Configuration Variables](../configuration-variables.md#google_cloudbatch) for all options, and [Machine Types](machine-types.md) for how these interact with machine type selection.

**cpuMilli**: CPU allocation in thousandths of a vCPU.

| cpuMilli | vCPUs |
|----------|-------|
| `1000` | 1 vCPU |
| `2000` | 2 vCPUs |
| `4000` | 4 vCPUs |

**memoryMib**: Memory allocation in mebibytes (MiB).

| memoryMib | Memory |
|-----------|--------|
| `2048` | 2 GB |
| `4096` | 4 GB |
| `8192` | 8 GB |
| `15360` | 15 GB |


For more information on compute resource options:

<!-- 
link-card: https://docs.cloud.google.com/batch/docs/reference/rest/v1/projects.locations.jobs#computeresource
    | title="ComputeResource | REST Resource: projects.locations.jobs | Google Cloud"
    | description=false
-->



## Further reading

- [Cloud Batch overview](https://cloud.google.com/batch/docs/overview)
- [Cloud Batch: Specify compute resources](https://cloud.google.com/batch/docs/create-run-job#resources)
