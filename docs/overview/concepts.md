# Concepts

Understanding a few concepts helps navigate the rest of the documentation. These come up throughout the pipeline, from configuration to execution to results.

## Simulation and calibration

The pipeline supports two main workflow types.

**Simulation** runs a model forward in time with given parameters to generate epidemic trajectories. You specify the model structure, initial conditions, and parameter values, and the simulator produce time series of compartment values (e.g., susceptible, infected, recovered) and transitions.

**Calibration** fits a model to observed data. You provide surveillance data (e.g., weekly hospitalizations) and prior distributions over parameters, and the pipeline uses Approximate Bayesian Computation (ABC) to find parameter values that best reproduce the observations. Calibration can optionally produce **projections** by running the fitted model forward beyond the fitting window.

## Experiments and runs


### Experiment

An **experiment** is a named set of configuration files that defines what to model. Each experiment lives in an experiment repository (configured via `github.forecast_repo` in your [profile](../user-guide/configuration/profiles.md)) and is identified by an **experiment ID** (`exp-id`), a free-form string you choose (e.g., `202604/smc_rmse_202550-202603`).

An experiment typically contains three configuration files under `experiments/{EXP_ID}/config/`:

- `basemodel.yml`: Model structure (compartments, transitions, initial conditions)
- `modelset.yml`: Simulation or calibration settings (parameters, fitting windows, populations)
- `output.yml`: Output generation settings (quantiles, trajectories, formats)

### Run

Each time you execute an experiment, the pipeline creates a new **run** with a unique run ID. This lets you repeat the same experiment without overwriting previous outputs.

Run ID is a unique identifier that follows the following format: `{YYYYMMDD-hhmmss}-{UUID}`. It is also used for paths when saving files.

## Pipeline

Running an experiment often involves heavy computation: calibrating across dozens of populations, or simulating thousands of parameter combinations. We call the sequence of steps that processes an experiment a **pipeline**. It splits the work into three stages:

1. **Builder**: Prepares independent task inputs from your experiment configuration
2. **Runner**: Executes all tasks in parallel
3. **Output**: Aggregates results into final outputs

For details, see [Pipeline Stages](../architecture/pipeline-stages.md).
