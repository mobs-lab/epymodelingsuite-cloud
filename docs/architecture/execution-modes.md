# Execution Modes

The pipeline runs in two execution modes (**cloud** and **local**) using the same Docker images and pipeline scripts. This allows users to develop and debug locally with fast iterations, while maintaining a scalable deployment on cloud.

## Comparison

| Aspect | Cloud Mode | Local Mode |
|--------|-----------|------------|
| **Infrastructure** | Google Cloud | User's local machine |
| **Stage Coordination** | Cloud Workflows (automated, async) | `epycloud` CLI (sequential, blocking) |
| **Execution Management** | Cloud Batch (auto-provisions VMs) | Docker Compose (runs on your machine) |
| **Storage** | Google Cloud Storage (`gs://bucket/`) | Local filesystem (`./local/bucket/`) |
| **Data Sourcing** | Builder clones experiment repo from GitHub | Local folder `./local/forecast/` mounted in container |
| **Docker Image** | `cloud` target (includes gcloud CLI) | `local` target (minimal, no cloud tools) |
| **Stage B Parallelism** | Parallel | Sequential (one task at a time) |
| **Task Index Variable** | `BATCH_TASK_INDEX` (set by Cloud Batch) | `TASK_INDEX` (set manually) |

## Cloud Mode

In cloud mode, the pipeline fully runs on Google Cloud. Google Cloud Workflows orchestrates all three stages end-to-end:

1. User submits a workflow via `epycloud run workflow --exp-id <id>`
2. Cloud Workflows creates a Stage A Batch job and polls until complete
3. Stage A outputs `NUM_TASKS` as a job label; Workflows reads it
4. Workflows creates a Stage B Batch job with N parallel tasks
5. After Stage B completes, Workflows creates Stage C
6. All artifacts are saved to and loaded from GCS

Cloud Batch automatically provisions VMs, pulls the Docker image from Artifact Registry, and schedules tasks. The builder stage clones the experiment repository from GitHub at runtime (using a GitHub PAT if the repository is private).

See **[Workflows Orchestration](workflows-orchestration.md)** for polling, retry, and error-handling details.

## Local Mode

In local mode, the pipeline fully runs on the user's machine. Note that the stage B is not parallelized (**runs sequentially**) in this mode:

1. Run all stages with `epycloud run workflow --local --exp-id <id>`, or run stages individually for debugging
2. Stage A generates input files to `./local/bucket/`
3. Stage B tasks run one at a time. Set `TASK_INDEX` for each
4. Stage C aggregates results from the local filesystem

Instead of cloning the experiment repo, local mode mounts `./local/forecast/` into containers. Copy experiment configs there before running:

```bash
cp -r ~/Developer/flu-forecast-epydemix/experiments/{EXP_ID} ./local/forecast/experiments/
```

See **[Running Locally](../user-guide/running-experiments/local.md)** for step-by-step instructions.

## How the Abstraction Works

### `EXECUTION_MODE` Environment Variable

The single environment variable `EXECUTION_MODE` (`cloud` or `local`) controls all mode-dependent behavior.

### Storage Abstraction (`storage.py`)

The `storage.py` module provides a unified API:

| Function | Cloud Backend | Local Backend |
|----------|--------------|---------------|
| `save_bytes(path, data)` | GCS upload | Filesystem write |
| `load_bytes(path)` | GCS download | Filesystem read |
| `list_files(prefix)` | GCS blob listing | Filesystem glob |
| `get_path(*parts)` | `gs://bucket/prefix/...` | `./local/bucket/prefix/...` |

See **[Storage Abstraction](storage-abstraction.md)** for the full API reference.

### Task Indexing

Each Stage B container needs a unique task index to load the correct input file. The mechanism differs by mode:

- **Cloud**: Cloud Batch automatically sets `BATCH_TASK_INDEX` (0-indexed) for each parallel task
- **Local**: Users set `TASK_INDEX` manually (e.g., `--task-index 0`)

Pipeline scripts check both variables: `TASK_INDEX` takes precedence if set, falling back to `BATCH_TASK_INDEX`.

### Docker Image Variants

Both modes use the same base dependencies and `epymodelingsuite` package. The only difference:

- **`local` target**: Minimal image, no cloud tools, smaller and faster to build
- **`cloud` target**: Adds gcloud CLI for Secret Manager access and Cloud Storage authentication

See **[Docker Images](docker-images.md)** for build details.

## Next Steps

- **[Running Locally](../user-guide/running-experiments/local.md)**: Step-by-step local execution guide
- **[Running on Cloud](../user-guide/running-experiments/cloud.md)**: Cloud workflow execution guide
- **[Storage Abstraction](storage-abstraction.md)**: Full storage API details
- **[Workflows Orchestration](workflows-orchestration.md)**: Cloud orchestration details
- **[Docker Images](docker-images.md)**: Image build and variants
