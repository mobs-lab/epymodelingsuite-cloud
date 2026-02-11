# Cloud Workflows

Google Cloud Workflows is a serverless orchestration service that coordinates multi-step processes. For how the pipeline's workflow is structured (steps, polling, variables, error handling), see [Workflows Orchestration](../../architecture/workflows-orchestration.md).

<!-- 
link-card: https://docs.cloud.google.com/workflows/docs
    | title="Workflows documentation | Google Cloud"
    | description=false
-->


## Workflows and executions

A **workflow** is a series of steps that orchestrate Google Cloud services and events. The pipeline's workflow is defined in [`terraform/workflow.yaml`](https://github.com/mobs-lab/epymodelingsuite-cloud/blob/main/terraform/workflow.yaml) and deployed via Terraform.

An **execution** is a single run of a deployed workflow. Google Cloud assigns a unique execution ID to each run. When triggered (e.g., via `epycloud run workflow`), the execution receives input parameters such as the experiment ID, bucket name, and parallelism settings. Multiple executions can run concurrently.

Execution states: **ACTIVE** → **SUCCEEDED**, **FAILED**, or **CANCELLED**.

For more details on the concepts:
<!-- 
link-card: https://docs.cloud.google.com/workflows/docs/overview#core-concepts
    | title="Core concepts | Cloud Workflows | Google Cloud"
    | description=false
-->



## Connectors

Cloud Workflows communicates with other Google Cloud services through built-in **connectors**. The pipeline workflow uses:

| Connector | Purpose |
|-----------|---------|
| **Cloud Batch** | Submit and monitor Batch jobs for each stage |
| **Cloud Storage** | List and count builder artifacts between stages |

Connectors handle authentication and retries automatically.

<!-- 
link-card: https://docs.cloud.google.com/workflows/docs/reference/googleapis/batch/Overview
    | title="Batch API Connector Overview | Cloud Workflows | Google Cloud"
    | description=false
-->


<!-- 
link-card: https://docs.cloud.google.com/workflows/docs/reference/googleapis/storage/Overview
    | title="Cloud Storage JSON API Connector Overview | Cloud Workflows | Google Cloud"
    | description=false
-->



## Quotas and limits

| Limit | Value |
|-------|-------|
| Max concurrent executions per workflow | 10,000 |
| Max execution duration | 1 year |
| Max steps per execution | 100,000 |
| Max workflow definition size | 1 MB |

See [Workflows quotas and limits](https://cloud.google.com/workflows/quotas) for the full list.

## Further reading

- [Cloud Workflows overview](https://cloud.google.com/workflows/docs/overview)
- [Workflows pricing](https://cloud.google.com/workflows/pricing)
- [Workflows connectors reference](https://cloud.google.com/workflows/docs/reference/googleapis)
