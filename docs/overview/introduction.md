# Introduction

**[epymodelingsuite-cloud](https://github.com/mobs-lab/epymodelingsuite-cloud)** provides infrastructure to run epidemic modeling workflows at scale on **Google Cloud**, with a dedicated CLI tool (**epycloud**) that provides a developer-friendly interface. It runs **[epymodelingsuite](https://github.com/mobs-lab/epymodelingsuite)**, a Python package designed for simulating and calibrating epidemic models using YAML-defined experiment sets on the [epydemix](https://github.com/epistorm/epydemix) engine, which allows for routine forecasts.

## Just One Command

Once set up, running epidemic forecasts is this simple:

```bash
epycloud run workflow --exp-id myexperiment
```

## Built on epydemix

This project is built on [epydemix](https://github.com/epistorm/epydemix), a Python package for epidemic modeling. See [Ecosystem](ecosystem.md) for how the components fit together.

## Pipeline design

The pipeline is consisted of three stages:

1. **Builder**: Reads your YAML configs, constructs epidemic models for each population, and packages them into N task inputs
2. **Runner**: Executes N simulations in parallel (this is where the compute happens)
3. **Output**: Aggregates all results into formatted outputs (CSV files, plots)

For a detailed look at each stage, see [Architecture: Pipeline Stages](../architecture/pipeline-stages.md).

## Local and cloud support

The pipeline is designed to run both **locally** and on the **cloud**. All stages run inside Docker containers, so switching between local and cloud is transparent; just add `--local` option to run on your machine.

For more details, see [Architecture: Execution Modes](../architecture/execution-modes.md).

## Learn More

To understand the system in depth:

<div class="grid cards" markdown>

-   :material-package-variant:{ .lg .middle } **[Ecosystem](ecosystem.md)**

    ---

    Learn about the repositories that make up the system

-   :material-console:{ .lg .middle } **[epycloud CLI](epycloud.md)**

    ---

    Learn about the command-line tool and key commands

</div>

## Next Steps

Ready to start using epycloud?

- **[Installing epycloud](../getting-started/installation.md)**: Install the epycloud CLI tool
- **[Quick Start](../getting-started/local.md)**: Run your first local workflow in 10 minutes
- **[Cloud Deployment](../getting-started/cloud-deployment/index.md)**: Deploy infrastructure to Google Cloud

For technical deep dive:

- **[Architecture Overview](../architecture/index.md)**: Detailed system architecture
