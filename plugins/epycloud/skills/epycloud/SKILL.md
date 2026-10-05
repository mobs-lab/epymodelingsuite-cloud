---
name: epycloud
description: Submit, monitor, and manage epymodelingsuite cloud workflows and batch jobs via the `epycloud` CLI. Use when the user mentions epycloud, asks to "submit a job", "run a workflow", "watch status", "stream logs", "use the flu profile", or wants to set up envs/profiles/secrets. Covers run / job / status / logs / workflow / profile / config commands.
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
---

# epycloud

CLI for running epymodelingsuite pipelines on Google Cloud. Wraps Cloud Workflows (orchestration), Cloud Batch (jobs), Cloud Storage (output), Cloud Build (image build), and Cloud Logging (logs).

Pipeline stages: **A (builder)** → **B (runner, parallel)** → **C (output)**. A workflow runs all three; a job runs one stage.

Docs are served as raw markdown: fetch `https://mobs-lab.github.io/epymodelingsuite-cloud/<page>.md` (e.g. `https://mobs-lab.github.io/epymodelingsuite-cloud/epycloud/run.md`). Page index: `https://mobs-lab.github.io/epymodelingsuite-cloud/llms.txt`. Check the docs before guessing a flag.

## Most common

```bash
epycloud run workflow --exp-id <EXP_ID>                              # submit full pipeline (A -> B -> C)
epycloud status                                                       # active workflows + batch jobs
epycloud run job --stage A --exp-id <EXP_ID> --run-id <RUN_ID> ...    # rerun one stage of an existing run
```

## Global flags

```
epycloud [--env ENV] [--profile PROFILE] [-d PROJECT_DIR] [--verbose] [--quiet] [--dry-run] COMMAND ...
```

- `--env` *(optional)* — environment overlay (`dev`, `prod`, or any user-defined name). Defaults to `default`. Lists via `epycloud config list-envs`.
- `--profile` *(optional)* — disease/project profile (`flu`, `covid`, etc.). Defaults to the persistent active profile (`epycloud profile use <name>` to change). Pass `--profile` only to override for one invocation.
- `--dry-run` — print planned action without executing. Use first when uncertain.

When the active profile + default env match what you want, both flags can be omitted entirely:

```bash
epycloud run workflow --exp-id <EXP_ID> --yes
```

## Submit a workflow (most common)

```bash
epycloud run workflow --exp-id <EXP_ID> --yes
# or with overrides:
epycloud --env <env> --profile <profile> run workflow --exp-id <EXP_ID> --yes
```

- `--exp-id` is the path under `experiments/` (e.g., `202613/my-experiment`).
- `--yes` skips the confirmation prompt; omit for an interactive prompt.
- Useful adders: `--wait` (block + stream logs), `--skip-output` (skip stage C), `--max-parallelism N`, `--forecast-repo-ref BRANCH`, `--run-id ID` (else auto), `--stage-{a,b,c}-machine-type TYPE`, `--batch-region REGION`, `--output-config FILE`.

Output ends with an **execution ID** (UUID). Save it for monitoring.

For repeated submissions across many epiweeks, loop in bash:

```bash
for w in 202550 202551 ...; do
  epycloud run workflow --exp-id "${w}/my-experiment" --yes \
    || { echo "FAILED at $w"; break; }
done
```

## Submit one stage (debugging)

```bash
epycloud run job --stage A --exp-id <EXP_ID>                      # builder
epycloud run job --stage B --exp-id <EXP_ID> --run-id <ID> --task-index 0
epycloud run job --stage C --exp-id <EXP_ID> --run-id <ID> --num-tasks 100
```

Add `--local` to any of the above to run via Docker Compose instead of cloud (run from the epymodelingsuite-cloud repo root, with the forecast repo contents under `./local/forecast/`). `--output-config FILE` selects the Stage C output YAML. Stage B reuses a completed result whose input digest matches; `--fresh` forces recompute.

## Machine and resource options

Each stage has an ordered **fallback chain** (`machine_types`). The workflow tries candidates in order; if one cannot get capacity, its Batch job is cancelled and drained before the next is tried. Every candidate must meet the stage's `cpu_milli`/`memory_mib` minimums.

Per-run overrides (cloud only):

```bash
# pin a stage to one machine type (disables fallback for that stage)
epycloud run workflow --exp-id <EXP_ID> --stage-b-machine-type c4d-standard-2

# parallelism / packing / region
epycloud run workflow --exp-id <EXP_ID> --max-parallelism 50 --task-count-per-node 2
epycloud run workflow --exp-id <EXP_ID> --batch-region us-east5

# single job: --machine-type applies to that stage
epycloud run job --stage B --exp-id <EXP_ID> --run-id <RUN_ID> --task-index 0 --machine-type c3-highcpu-4
```

- `--stage-{a,b,c}-machine-type` (workflow) / `--machine-type` (job): pins one candidate; it must still meet the stage minimums. Use for benchmarks and debugging.
- `--max-parallelism N`: max concurrent Stage B tasks. `--task-count-per-node N`: tasks per VM (1 = dedicated VM).
- `--batch-region REGION`: must be a key of `google_cloud.batch_regions` (default: `google_cloud.region`). The image tag must exist in that region (see Build images).
- `--billing-project NAME`: cost-grouping label.
- Stage C aggregates every Stage B result and is memory bound: never pin or configure a candidate with less memory than the configured chain.

Persistent defaults (chains, CPU/memory minimums, `max_run_duration`, regions) live under `google_cloud.batch` in config; see merged values with `epycloud config show`.

## Monitor

```bash
epycloud status                            # all active workflows + batch jobs
epycloud status --exp-id <EXP_ID>          # filter
epycloud status --watch --interval 10      # auto-refresh
epycloud status --recent 24h               # include recently finished
epycloud status --watch --stall-threshold 25   # warn when provisioning stalls > 25 min (default 15)

epycloud workflow list --since 24h         # recent executions
epycloud workflow list --status FAILED
epycloud workflow describe <EXEC_ID>       # full detail for one execution
epycloud workflow cancel <EXEC_ID>         # cascades to batch jobs; use this to stop a pipeline
epycloud workflow retry <EXEC_ID>          # re-runs with same params
```

## Logs

Two distinct sources — pick the right one:

- `epycloud logs --exp-id <EXP_ID>` — **pipeline** logs (builder/runner/output script stdout/stderr).
- `epycloud workflow logs <EXEC_ID>` — **orchestration** logs (workflow steps, job submissions).

Common flags: `-f`/`--follow` to stream, `--tail N` (0 = unlimited), `--since 1h`, `--run-id ID`, `--stage {A,B,C}`, `--task-index N`, `--level ERROR`. `epycloud logs --execution-id <EXEC_ID>` or `--job-name <JOB>` works without `--exp-id`.

## Validate before submitting

```bash
epycloud validate --exp-id <EXP_ID>                    # fetches from GitHub
epycloud validate --path ./experiments/<EXP_ID>/config # local
epycloud validate --exp-id <EXP_ID> && epycloud run workflow --exp-id <EXP_ID> --yes
```

## Browse and download results

```bash
epycloud experiment list                              # 50 most recent
epycloud experiment list -e "202613/*" --latest       # filter + one run per exp
epycloud experiment list --format args                # paste-ready --exp-id/--run-id

epycloud download -e "202613/*" -o ./results --yes
epycloud download -e "202613/*" -o ./results --files "quantiles*" --yes   # subset of files
```

## Profiles vs environments

Two independent axes. Merge order (low to high): base `config.yaml` < env < profile < `./epycloud.yaml` (project) < `EPYCLOUD_*` env vars.

- **Profile** = *what* you run (disease/project). Holds `github.forecast_repo`, `storage.dir_prefix`, project-specific batch resources. Persistent: set once with `profile use`.
- **Environment** = *which code/infra* runs it. Holds `docker.image_tag`, `github.modeling_suite_ref`, workflow/region overrides. Per invocation with `--env` (default: `default`).

Since a profile is merged after the env, a key set in both takes the profile's value. Keep code/image keys in envs and project keys in profiles.

```bash
epycloud profile list | current | show <name> | edit <name>
epycloud profile use <name>                                    # activate (persists)
epycloud profile create <name> --template basic --forecast-repo <owner/repo>
epycloud config list-envs
epycloud --env <name> config show                              # merged result for that env
```

### Run with an epymodelingsuite development branch

Create an env that points at the branch and its own image tag, build that image, then run with the env:

```bash
# 1. ~/.config/epymodelingsuite-cloud/environments/<branch>.yaml
cat > ~/.config/epymodelingsuite-cloud/environments/my-feature.yaml <<'YAML'
docker:
  image_tag: my-feature              # separate tag so production "latest" is untouched
github:
  modeling_suite_ref: my-feature     # epymodelingsuite branch, tag, or commit
YAML

# 2. build the image from that branch
epycloud --env my-feature build cloud --wait

# 3. run with the same env
epycloud --env my-feature run workflow --exp-id <EXP_ID>
```

- Always pass the same `--env` to `build` and `run`: the image tag comes from the env, so a mismatch runs the wrong code.
- Rebuild after pushing new commits to the branch; the image is not rebuilt automatically.
- Running in a secondary Batch region also needs `epycloud build replicate --to <region> --tag my-feature`.
- To test a forecast repo branch instead, no build is needed: `--forecast-repo-ref <branch>`.

## Config (base + secrets)

```bash
epycloud config init                  # first-time setup; creates base + flu profile
epycloud config show                  # merged base + env + profile
epycloud config show --raw            # YAML
epycloud config edit                  # base config in $EDITOR
epycloud config edit-secrets          # GitHub PAT etc. (0600)
epycloud config validate              # syntax + required fields
epycloud config get google_cloud.project_id
epycloud config set docker.image_tag v2.0.0
```

Files live at `~/.config/epymodelingsuite-cloud/` (XDG). Secrets stay local (`secrets.yaml`); for cloud-side, store the GitHub PAT in Secret Manager as `github-pat` — see `https://mobs-lab.github.io/epymodelingsuite-cloud/user-guide/configuration/secrets.md`.

## Build images

Workflows use a Docker image from Artifact Registry. Rebuild when `github.modeling_suite_ref` changes.

```bash
epycloud build cloud --wait                 # cloud build, block until done (layer cache off; add --cache)
epycloud --env <env> build cloud --wait     # build with non-default env overlay
epycloud build status                       # recent builds
epycloud build dev                          # local-only, fast iteration

# secondary Batch region: copy the built image by digest (no rebuild), then verify
epycloud build replicate --from us-central1 --to us-east5 --tag <TAG>
epycloud build verify-replicas --tag <TAG>
```

## When something goes wrong

1. `epycloud workflow describe <EXEC_ID>` — surface the error message and which stage failed.
2. `epycloud workflow logs <EXEC_ID>` — orchestration-side errors (job submission, IAM).
3. `epycloud logs --exp-id <EXP_ID> --run-id <RUN_ID> --stage <STAGE> --level ERROR` — runtime errors inside the container.
4. `epycloud validate --exp-id <EXP_ID>` — config-shape problems before resubmitting.
5. `epycloud workflow retry <EXEC_ID>` — if the failure was transient.

Cancel cascades to child batch jobs by default; pass `--only-workflow` to leave running jobs alone. Do not cancel a child Batch job directly: the workflow then stops without trying another candidate, reports `CHILD_JOB_CANCELLED`, and ends `FAILED`.

`epycloud status` shows `TASKS` (completed work) and `SLOTS` (occupied capacity vs demand), plus a warning for jobs stuck underfilled during provisioning.

## Install and upgrade epycloud

Installed as a uv tool from a clone of the epymodelingsuite-cloud repo (`~/.local/bin/epycloud`). See `https://mobs-lab.github.io/epymodelingsuite-cloud/getting-started/installation.md`.

```bash
# install
git clone https://github.com/mobs-lab/epymodelingsuite-cloud
cd epymodelingsuite-cloud
uv tool install .

# upgrade
cd epymodelingsuite-cloud
git pull
uv tool upgrade epycloud --reinstall
epycloud --version
```

- `uv tool upgrade` rebuilds from the directory recorded at install time (`requirements` in `~/.local/share/uv/tools/epycloud/uv-receipt.toml`), so `git pull` in that same checkout. To switch checkouts or branches, run `uv tool install --force --reinstall .` from the new one.
- Without `--reinstall`, uv may reuse a cached build of the local directory and miss code changes when the version did not change.

## First-time setup checklist

```bash
epycloud config init
epycloud config edit               # set google_cloud.project_id, region, bucket
epycloud config edit-secrets       # GitHub PAT
epycloud profile use <project>     # only if you have multiple profiles
epycloud config show               # sanity check merged config
epycloud build cloud --wait
epycloud run workflow --exp-id <EXP_ID> --dry-run
```

## Reference index

Fetch `https://mobs-lab.github.io/epymodelingsuite-cloud/<page>`.

| Topic | Page |
|---|---|
| Top-level CLI | `epycloud/index.md` |
| `run` (workflow / job) | `epycloud/run.md` |
| `workflow` (list/describe/cancel/retry) | `epycloud/workflow.md` |
| `status` | `epycloud/status.md` |
| `logs` | `epycloud/logs.md` |
| `profile` | `epycloud/profile.md` |
| `config` | `epycloud/config.md` |
| `validate` | `epycloud/validate.md` |
| `experiment` / `download` | `epycloud/experiment.md`, `epycloud/download.md` |
| `build` / `terraform` | `epycloud/build.md`, `epycloud/terraform.md` |
| Installation | `getting-started/installation.md` |
| Configuration system | `user-guide/configuration/index.md` |
| Profiles guide | `user-guide/configuration/profiles.md` |
| Environments guide | `user-guide/configuration/environments.md` |
| Secrets guide | `user-guide/configuration/secrets.md` |
