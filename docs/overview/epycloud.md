# epycloud CLI

**epycloud** is the command-line interface tool that provides a user-friendly way to interact with the entire pipeline. It handles everything from configuration and infrastructure deployment to running workflows and monitoring execution.

## What It Does

The epycloud CLI manages the complete workflow lifecycle:

- **Configuration**:  Initialize, edit, and validate settings
- **Infrastructure**:  Build Docker images locally or in the cloud
- **Running**:  Execute workflows in local or cloud mode
- **Monitoring**:  View logs, track execution status, and debug issues

## Usage examples

**Build & Run**
```bash
epycloud build cloud          # Build Docker image
epycloud run workflow --exp-id myexperiment  # Run workflow
```

**Monitor**
```bash
epycloud status -w              # Watch status of workflows and jobs
epycloud logs --exp-id myexperiment --follow  # Stream logs
```


## Next Steps

- **[Installing epycloud](../getting-started/installation.md)**: Install the epycloud CLI tool
- **[Getting started: Local Execution](../getting-started/local.md)**: Run your first local workflow locally
- **[epycloud Reference](../epycloud/index.md)**: Complete command documentation
