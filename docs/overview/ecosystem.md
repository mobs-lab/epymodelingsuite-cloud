# Ecosystem

To support scalable epidemic modeling and research, the ecosystem is built on four independent repositories that can evolve independently:

| Component | Role |
|---|---|
| **[epydemix](https://github.com/epistorm/epydemix)** | Epidemic modeling engine in Python with support for model calibration using Approximate Bayesian Computation |
| **[epymodelingsuite](https://github.com/mobs-lab/epymodelingsuite)** | YAML-configured modeling suite for routine epidemic forecasting with support for interventions like school closures and vaccines. Uses epydemix as engine. |
| **[epymodelingsuite-cloud](https://github.com/mobs-lab/epymodelingsuite-cloud)** | Cloud infrastructure and `epycloud` CLI for running parallel workloads on Google Cloud with local development support |
| **Experiment data repository** | YAML experiment configurations, shared surveillance data, and custom functions. Typically one per project (e.g. flu, COVID-19, RSV). |

For detailed descriptions of each component, see [Ecosystem Components](../architecture/ecosystem-components.md).

## Next Steps

- **[Installing epycloud](../getting-started/installation.md)**: Install the CLI tool
- **[Getting started: Local Execution](../getting-started/local.md)**: Run your first local workflow locally
