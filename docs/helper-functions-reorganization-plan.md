# Helper Functions Reorganization Plan

**Date:** 2025-11-15
**Status:** Planning
**Goal:** Eliminate ~210 lines of code duplication by centralizing helper functions

---

## Executive Summary

### Current Situation
- **10 command files** with ~6,000 lines total
- **~235 lines of duplicated code** across 5 files
- Config extraction repeated **11 times** across build.py, run.py, workflow.py, status.py, logs.py
- GitHub PAT retrieval duplicated **3 times**
- run.py has 3 new helper functions from recent refactoring (Nov 15, 2025)

### Recommendation
Implement **Phase 1** to centralize high-impact helpers in `src/epycloud/lib/command_helpers.py`, eliminating ~210 lines of duplication across 5 command files.

---

## Analysis: Code Duplication Metrics

### Current Duplication Count

| Pattern | Instances | Lines Duplicated | Files Affected |
|---------|-----------|------------------|----------------|
| Config extraction (Docker/GitHub/GCloud) | 11 | ~150 | build.py, run.py, workflow.py, status.py, logs.py |
| GitHub PAT retrieval | 3 | ~45 | build.py, validate.py |
| Batch SA email | 2 | ~25 | run.py (internal duplication) |
| Image URI building | 3 | ~15 | build.py, run.py |
| **Total** | **19** | **~235** | **5 files** |

### After Phase 1 Migration

| Pattern | Instances | Lines Reduced |
|---------|-----------|---------------|
| Config extraction | 0 (centralized) | -150 |
| GitHub PAT retrieval | 0 (centralized) | -45 |
| Image URI building | 0 (centralized) | -15 |
| Batch SA email | 0 (centralized) | -25 |
| **Total Reduction** | **-19 instances** | **~235 lines** |

---

## Command File Structure

### Total Command Files: 10 files (6,006 lines)

| File | Lines | Complexity | Primary Purpose |
|------|-------|------------|----------------|
| run.py | 1,282 | High | Pipeline execution (workflow & jobs) |
| workflow.py | 992 | High | Cloud Workflows management |
| build.py | 816 | Medium | Docker image building |
| validate.py | 609 | Medium | Config validation |
| terraform.py | 600 | Medium | Infrastructure management |
| config_cmd.py | 503 | Medium | Configuration management |
| status.py | 431 | Medium | Pipeline status monitoring |
| logs.py | 417 | Medium | Log viewing & streaming |
| profile.py | 355 | Low | Profile management |
| __init__.py | 1 | Minimal | Package initialization |

### Existing Helper Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| formatters.py | 537 | Output formatting, timestamps, status colors |
| validation.py | 306 | Input validation (exp_id, run_id, paths, tokens) |
| output.py | 280 | Console output (info, error, success, warning) |
| command_helpers.py | 267 | Config access, dry-run handling, project root |
| paths.py | 222 | Config path resolution |

---

## Detailed Duplication Analysis

### 1. Config Extraction Functions (11 instances)

**Pattern:** Extract nested config values repeatedly

**Locations:**
- `build.py`: Lines 186-201, 252-265, 328-345 (3 instances)
- `run.py`: Lines 364-377, 568-573, 740-749, 952-957 (4 instances - recently refactored to use `_extract_config_values()`)
- `terraform.py`: Lines 519-600 (1 massive instance - 82 lines!)
- `workflow.py`: Lines 199-209 (1 instance)
- `status.py`: Lines 66-73 (1 instance)
- `logs.py`: Lines 99-105 (1 instance)

**Example Duplication:**
```python
# Repeated in build.py (3 times), workflow.py, status.py, logs.py
docker_config = config.get("docker", {})
google_cloud_config = config.get("google_cloud", {})
github_config = config.get("github", {})

registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
project_id = google_cloud_config.get("project_id")
region = google_cloud_config.get("region", "us-central1")
repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
image_name = docker_config.get("image_name", "epymodelingsuite")
image_tag = docker_config.get("image_tag", "latest")
```

### 2. GitHub PAT Retrieval (3 instances)

**Locations:**
- `build.py`: Lines 277-291, 342-356 (2 instances)
- `validate.py`: Lines 148-172 (1 instance)

**Code Pattern:**
```python
github_pat = os.environ.get("GITHUB_PAT") or os.environ.get("EPYCLOUD_GITHUB_PAT")
if not github_pat and modeling_suite_repo:
    github_pat = config.get("github", {}).get("personal_access_token")

if modeling_suite_repo and not github_pat:
    secrets_file = get_secrets_file()
    error("GitHub PAT required when modeling_suite_repo is configured")
    info("Options:")
    info("  1. Load from .env.local: source .env.local")
    info("  2. Set environment variable: export GITHUB_PAT=your_token")
    info("  3. Add to secrets.yaml: epycloud config edit-secrets")
    info(f"     (File location: {secrets_file})")
    return 2
```

### 3. Batch Service Account Email (2 instances)

**Locations:**
- `run.py`: Lines 1189-1213 (`_get_batch_sa_email()` - defined once)
- `run.py`: Lines 388, 764 (called twice)

**Pattern:** Try terraform output, fall back to default

### 4. Image URI Building (3 instances)

**Locations:**
- `build.py`: Lines 191-195, 257-261, 333-337
- `run.py`: Lines 1270-1284 (`_build_image_uri()` - defined once, called twice)

**Pattern:**
```python
image_uri = f"{registry}/{project_id}/{repo_name}/{image_name}:{image_tag}"
```

### 5. Run ID Generation (1 instance)

**Location:**
- `run.py`: Lines 1216-1226 (`_generate_run_id()`)

**Pattern:** Generate unique timestamp-based ID

### 6. Input Validation (2 instances)

**Locations:**
- `run.py`: Lines 1287-1302 (`_validate_inputs()` - defined once, called twice)

**Pattern:** Validate exp_id and run_id from args

---

## Recommended Organization Structure

### Phase 1: Centralize High-Impact Helpers ⭐ PRIORITY

**Add to `src/epycloud/lib/command_helpers.py`:**

```python
def get_docker_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract Docker configuration with defaults.

    Returns:
        Dict with keys: registry, repo_name, image_name, image_tag
    """
    docker = config.get("docker", {})
    return {
        "registry": docker.get("registry", "us-central1-docker.pkg.dev"),
        "repo_name": docker.get("repo_name", "epymodelingsuite-repo"),
        "image_name": docker.get("image_name", "epymodelingsuite"),
        "image_tag": docker.get("image_tag", "latest"),
    }


def get_github_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract GitHub configuration.

    Returns:
        Dict with keys: forecast_repo, modeling_suite_repo,
                       modeling_suite_ref, personal_access_token
    """
    github = config.get("github", {})
    return {
        "forecast_repo": github.get("forecast_repo", ""),
        "modeling_suite_repo": github.get("modeling_suite_repo", ""),
        "modeling_suite_ref": github.get("modeling_suite_ref", "main"),
        "personal_access_token": github.get("personal_access_token", ""),
    }


def get_batch_config(config: dict[str, Any]) -> dict[str, Any]:
    """Extract Cloud Batch configuration.

    Returns:
        Full batch config dict with stage-specific settings
    """
    return config.get("google_cloud", {}).get("batch", {})


def get_image_uri(config: dict[str, Any], tag: str | None = None) -> str:
    """Build full Docker image URI from config.

    Args:
        config: Configuration dict
        tag: Optional tag override (uses config default if None)

    Returns:
        Full image URI (e.g., "us-central1-docker.pkg.dev/project/repo/image:tag")
    """
    docker = get_docker_config(config)
    google_cloud = config.get("google_cloud", {})
    project_id = google_cloud.get("project_id")

    image_tag = tag or docker["image_tag"]

    return (
        f"{docker['registry']}/"
        f"{project_id}/"
        f"{docker['repo_name']}/"
        f"{docker['image_name']}:{image_tag}"
    )


def get_github_pat(config: dict[str, Any], required: bool = False) -> str | None:
    """Get GitHub PAT from environment, secrets, or config.

    Priority:
    1. GITHUB_PAT environment variable
    2. EPYCLOUD_GITHUB_PAT environment variable
    3. github.personal_access_token from config

    Args:
        config: Configuration dict
        required: If True, print error and return None when not found

    Returns:
        GitHub PAT or None if not found
    """
    from epycloud.lib.output import error, info
    from epycloud.lib.paths import get_secrets_file

    # Try environment first
    github_pat = os.environ.get("GITHUB_PAT") or os.environ.get("EPYCLOUD_GITHUB_PAT")

    # Fall back to config
    if not github_pat:
        github_pat = config.get("github", {}).get("personal_access_token")

    # Handle required case
    if required and not github_pat:
        secrets_file = get_secrets_file()
        error("GitHub PAT required for this operation")
        info("Options:")
        info("  1. Load from .env.local: source .env.local")
        info("  2. Set environment variable: export GITHUB_PAT=your_token")
        info("  3. Add to secrets.yaml: epycloud config edit-secrets")
        info(f"     (File location: {secrets_file})")
        return None

    return github_pat


def get_batch_service_account(project_id: str, project_root: Path | None = None) -> str:
    """Get batch service account email from terraform or default.

    Args:
        project_id: Google Cloud project ID
        project_root: Optional project root (auto-detected if None)

    Returns:
        Batch service account email
    """
    import subprocess
    from epycloud.lib.command_helpers import get_project_root

    if project_root is None:
        project_root = get_project_root()

    terraform_dir = project_root / "terraform"

    # Try getting from terraform output
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", "batch_service_account_email"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fall back to default
    return f"batch-runtime@{project_id}.iam.gserviceaccount.com"


def generate_run_id() -> str:
    """Generate a unique run ID.

    Returns:
        Run ID in format: YYYYMMDD-HHMMSS-<uuid-prefix>
    """
    from datetime import datetime
    from uuid import uuid4

    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    unique_id = str(uuid4())[:8]
    return f"{date_part}-{time_part}-{unique_id}"


def validate_inputs(args: argparse.Namespace) -> tuple[str, str | None] | None:
    """Validate exp_id and run_id from args.

    Args:
        args: Parsed command-line arguments

    Returns:
        Tuple of (exp_id, run_id) on success, None on failure (error already printed)
    """
    from epycloud.lib.validation import validate_exp_id, validate_run_id, ValidationError
    from epycloud.lib.output import error

    try:
        exp_id = validate_exp_id(args.exp_id)
        run_id = validate_run_id(args.run_id) if args.run_id else None
        return exp_id, run_id
    except ValidationError as e:
        error(str(e))
        return None
```

**Functions added: 8**
**Lines of code: ~150 lines** (but eliminates ~235 lines of duplication)

---

### Phase 2: Keep Domain-Specific Helpers Local

**Keep in respective command files** (as private `_function_name` helpers):

#### Display/Formatting Functions (Command-Specific)
- `build.py`: `_display_build_status()` (lines 453-506)
- `workflow.py`: `_display_execution_list()`, `_display_execution_details()` (lines 748-868)
- `status.py`: `_display_status()` (lines 322-432)
- `logs.py`: `_display_logs()` (lines 234-320)
- `validate.py`: `_display_validation_results()` (lines 291-348)

**Rationale:** These format command-specific data structures and would add complexity if generalized

#### Build Functions (Domain-Specific)
- `run.py`: `_build_batch_job_config()` (lines 1077-1186)
- `run.py`: `_build_env_from_config()` (lines 885-919)
- `terraform.py`: `_get_terraform_env_vars()` (lines 519-600)

**Rationale:** Complex, domain-specific builders that don't have duplication

#### Workflow Functions (Orchestration)
- `run.py`: `_run_workflow_local()`, `_run_workflow_cloud()`, `_run_job_local()`, `_run_job_cloud()`

**Rationale:** Substantial orchestration logic specific to run command

#### Specialized API Functions
- `workflow.py`: `_enrich_executions_with_arguments()`, `_parse_execution_name()`
- `validate.py`: `_validate_directory()`, `_validate_config_set()`, `_fetch_config_files()`
- `status.py`: `_fetch_active_workflows()`, `_fetch_active_batch_jobs()`

**Rationale:** Specialized API interactions, not reusable across commands

---

## Implementation Plan

### Step 1: Add Helper Functions to command_helpers.py

**File:** `src/epycloud/lib/command_helpers.py`

Add 8 new functions (see Phase 1 section above):
1. `get_docker_config()`
2. `get_github_config()`
3. `get_batch_config()`
4. `get_image_uri()`
5. `get_github_pat()`
6. `get_batch_service_account()`
7. `generate_run_id()`
8. `validate_inputs()`

**Lines added:** ~150 (with docstrings and error handling)

---

### Step 2: Update run.py

**File:** `src/epycloud/commands/run.py`

**Changes:**

1. **Add imports:**
```python
from epycloud.lib.command_helpers import (
    get_docker_config,
    get_github_config,
    get_batch_config,
    get_image_uri,
    get_batch_service_account,
    generate_run_id,
    validate_inputs,
)
```

2. **Remove helper function definitions:**
- Delete `_extract_config_values()` (lines 1229-1267)
- Delete `_build_image_uri()` (lines 1270-1284)
- Delete `_validate_inputs()` (lines 1287-1302)
- Delete `_get_batch_sa_email()` (lines 1189-1213)
- Delete `_generate_run_id()` (lines 1216-1226)

3. **Update call sites:**

**In `_run_workflow_cloud()` (lines 363-388):**
```python
# Before:
cfg = _extract_config_values(config)
project_id = cfg["project_id"]
region = cfg["region"]
bucket_name = cfg["bucket_name"]
dir_prefix = cfg["dir_prefix"]
github_forecast_repo = cfg["github_forecast_repo"]
batch_config = cfg["batch_config"]
image_uri = _build_image_uri(cfg)
batch_sa_email = _get_batch_sa_email(project_id)

# After:
google_cloud = config.get("google_cloud", {})
project_id = google_cloud.get("project_id")
region = google_cloud.get("region", "us-central1")
bucket_name = google_cloud.get("bucket_name")
pipeline = config.get("pipeline", {})
dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")
github = get_github_config(config)
github_forecast_repo = github["forecast_repo"]
batch_config = get_batch_config(config)
image_uri = get_image_uri(config)
batch_sa_email = get_batch_service_account(project_id)
```

**In `_run_workflow_local()` (lines 560-565):**
```python
# Before:
cfg = _extract_config_values(config)
image_name = cfg["image_name"]
image_tag = cfg["image_tag"]
dir_prefix = cfg["dir_prefix"]

# After:
docker = get_docker_config(config)
image_name = docker["image_name"]
image_tag = docker["image_tag"]
pipeline = config.get("pipeline", {})
dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")
```

**In `_run_job_cloud()` (lines 731-741):**
```python
# Before:
cfg = _extract_config_values(config)
project_id = cfg["project_id"]
region = cfg["region"]
bucket_name = cfg["bucket_name"]
dir_prefix = cfg["dir_prefix"]
batch_config = cfg["batch_config"]
image_uri = _build_image_uri(cfg)

# After:
google_cloud = config.get("google_cloud", {})
project_id = google_cloud.get("project_id")
region = google_cloud.get("region", "us-central1")
bucket_name = google_cloud.get("bucket_name")
pipeline = config.get("pipeline", {})
dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")
batch_config = get_batch_config(config)
image_uri = get_image_uri(config)
```

**In `_run_job_local()` (lines 936-941):**
```python
# Before:
cfg = _extract_config_values(config)
image_name = cfg["image_name"]
image_tag = cfg["image_tag"]
dir_prefix = cfg["dir_prefix"]

# After:
docker = get_docker_config(config)
image_name = docker["image_name"]
image_tag = docker["image_tag"]
pipeline = config.get("pipeline", {})
dir_prefix = pipeline.get("dir_prefix", "pipeline/flu/")
```

**In `_handle_workflow()` (lines 213-217):**
```python
# Before:
validated = _validate_inputs(args)
if validated is None:
    return 1
exp_id, run_id = validated

# After:
validated = validate_inputs(args)
if validated is None:
    return 1
exp_id, run_id = validated
```

**In `_handle_job()` (lines 280-284):**
```python
# Before:
validated = _validate_inputs(args)
if validated is None:
    return 1
exp_id, run_id = validated

# After:
validated = validate_inputs(args)
if validated is None:
    return 1
exp_id, run_id = validated
```

**In `_build_env_from_config()` (line 945):**
```python
# Before:
run_id = run_id or _generate_run_id()

# After:
run_id = run_id or generate_run_id()
```

**Lines removed:** ~115 (5 function definitions)
**Net change:** -115 lines in run.py

---

### Step 3: Update build.py

**File:** `src/epycloud/commands/build.py`

**Changes:**

1. **Add imports:**
```python
from epycloud.lib.command_helpers import (
    get_docker_config,
    get_github_config,
    get_github_pat,
    get_image_uri,
)
```

2. **Update `_handle_cloud()` (lines 186-201):**
```python
# Before:
google_cloud_config = config.get("google_cloud", {})
docker_config = config.get("docker", {})
github_config = config.get("github", {})

project_id = google_cloud_config.get("project_id")
region = google_cloud_config.get("region", "us-central1")
registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
image_name = docker_config.get("image_name", "epymodelingsuite")
image_tag = args.tag or docker_config.get("image_tag", "latest")
modeling_suite_repo = github_config.get("modeling_suite_repo", "")
modeling_suite_ref = github_config.get("modeling_suite_ref", "main")

# After:
google_cloud = config.get("google_cloud", {})
project_id = google_cloud.get("project_id")
region = google_cloud.get("region", "us-central1")
docker = get_docker_config(config)
image_tag = args.tag or docker["image_tag"]
github = get_github_config(config)
modeling_suite_repo = github["modeling_suite_repo"]
modeling_suite_ref = github["modeling_suite_ref"]
```

3. **Update `_handle_local()` (lines 252-291):**
```python
# Before:
docker_config = config.get("docker", {})
github_config = config.get("github", {})
google_cloud_config = config.get("google_cloud", {})

registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
image_name = docker_config.get("image_name", "epymodelingsuite")
image_tag = args.tag or docker_config.get("image_tag", "latest")
project_id = google_cloud_config.get("project_id")
modeling_suite_repo = github_config.get("modeling_suite_repo", "")
modeling_suite_ref = github_config.get("modeling_suite_ref", "main")

# Get GitHub PAT
github_pat = os.environ.get("GITHUB_PAT") or os.environ.get("EPYCLOUD_GITHUB_PAT")
if not github_pat and modeling_suite_repo:
    github_pat = github_config.get("personal_access_token")

if modeling_suite_repo and not github_pat:
    secrets_file = get_secrets_file()
    error("GitHub PAT required when modeling_suite_repo is configured")
    info("Options:")
    info("  1. Load from .env.local: source .env.local")
    info("  2. Set environment variable: export GITHUB_PAT=your_token")
    info("  3. Add to secrets.yaml: epycloud config edit-secrets")
    info(f"     (File location: {secrets_file})")
    return 2

# After:
docker = get_docker_config(config)
image_tag = args.tag or docker["image_tag"]
google_cloud = config.get("google_cloud", {})
project_id = google_cloud.get("project_id")
github = get_github_config(config)
modeling_suite_repo = github["modeling_suite_repo"]
modeling_suite_ref = github["modeling_suite_ref"]

# Get GitHub PAT
github_pat = get_github_pat(config, required=bool(modeling_suite_repo))
if modeling_suite_repo and not github_pat:
    return 2
```

4. **Update `_handle_dev()` (lines 328-356):**
Same pattern as `_handle_local()`

**Lines removed:** ~60 (from 3 functions)

---

### Step 4: Update validate.py

**File:** `src/epycloud/commands/validate.py`

**Changes:**

1. **Add imports:**
```python
from epycloud.lib.command_helpers import get_github_config, get_github_pat
```

2. **Update `_handle_remote()` (lines 148-172):**
```python
# Before:
github_config = config.get("github", {})
forecast_repo = github_config.get("forecast_repo", "")
if not forecast_repo:
    error("github.forecast_repo not configured")
    return 2

github_pat = os.environ.get("GITHUB_PAT") or os.environ.get("EPYCLOUD_GITHUB_PAT")
if not github_pat:
    github_pat = github_config.get("personal_access_token")

if not github_pat:
    secrets_file = get_secrets_file()
    error("GitHub PAT required for remote validation")
    info("Options:")
    info("  1. Load from .env.local: source .env.local")
    info("  2. Set environment variable: export GITHUB_PAT=your_token")
    info("  3. Add to secrets.yaml: epycloud config edit-secrets")
    info(f"     (File location: {secrets_file})")
    return 2

# After:
github = get_github_config(config)
forecast_repo = github["forecast_repo"]
if not forecast_repo:
    error("github.forecast_repo not configured")
    return 2

github_pat = get_github_pat(config, required=True)
if not github_pat:
    return 2
```

**Lines removed:** ~18

---

### Step 5: Update workflow.py, status.py, logs.py

**Files:** `src/epycloud/commands/workflow.py`, `src/epycloud/commands/status.py`, `src/epycloud/commands/logs.py`

**Changes:** Similar pattern - replace config extraction with helper calls

**Lines removed:** ~20 (total across 3 files)

---

### Step 6: Test All Commands

**Test Matrix:**

```bash
# Run commands
uv run epycloud --dry-run run workflow --exp-id test --yes
uv run epycloud --dry-run run workflow --local --exp-id test --yes
uv run epycloud --dry-run run job --stage A --exp-id test --yes
uv run epycloud --dry-run run job --local --stage A --exp-id test --yes

# Build commands
uv run epycloud build cloud
uv run epycloud build local
uv run epycloud build dev

# Validate command
uv run epycloud validate --path ./local/forecast/experiments/test/config

# Workflow commands
uv run epycloud workflow list
uv run epycloud workflow list --limit 10

# Status command
uv run epycloud status

# Logs command
uv run epycloud logs --exp-id test --tail 50
```

**Expected:** All commands should work identically to before

---

### Step 7: Commit Changes

**Commit message:**
```
Centralize config/validation helpers to eliminate duplication

- Add 8 helper functions to command_helpers.py
- Update run.py, build.py, validate.py, workflow.py, status.py, logs.py
- Eliminate ~235 lines of duplicated code across 5 files
- No functional changes, pure refactoring
```

---

## Summary

### Files Modified
1. `src/epycloud/lib/command_helpers.py` - Add 8 functions (+150 lines)
2. `src/epycloud/commands/run.py` - Remove 5 helpers, update imports (-115 lines)
3. `src/epycloud/commands/build.py` - Update 3 functions (-60 lines)
4. `src/epycloud/commands/validate.py` - Update 1 function (-18 lines)
5. `src/epycloud/commands/workflow.py` - Update config extraction (-7 lines)
6. `src/epycloud/commands/status.py` - Update config extraction (-7 lines)
7. `src/epycloud/commands/logs.py` - Update config extraction (-7 lines)

### Net Impact
- **Lines added:** +150 (command_helpers.py)
- **Lines removed:** -235 (across 6 files)
- **Net change:** -85 lines
- **Duplication eliminated:** 19 instances → 0 instances
- **Maintenance benefit:** HIGH - Config changes in one place

### Risk Assessment
- **Risk:** LOW
- **Reason:** Pure refactoring, no logic changes
- **Testing:** Comprehensive dry-run tests across all affected commands
- **Rollback:** Easy - single commit to revert

---

## Future Enhancements (Phase 2 - Optional)

### Create `lib/cloud_helpers.py`

For Cloud-specific operations that don't fit in command_helpers:

```python
def run_gcloud_command(
    args: list[str],
    project_id: str,
    capture_output: bool = True,
    verbose: bool = False
) -> subprocess.CompletedProcess:
    """Run gcloud command with standard setup."""

def submit_batch_job(
    job_config: dict,
    job_id: str,
    project_id: str,
    region: str,
    verbose: bool = False,
    dry_run: bool = False
) -> int:
    """Submit Cloud Batch job via gcloud."""
```

**Benefits:**
- More consistent error handling across cloud commands
- Easier testing and mocking
- Centralized retry logic

**Timeline:** Future enhancement, not part of Phase 1

---

## File Organization Principles

### Public Helpers (`command_helpers.py`)
Functions used by **2+ command files**
- Config extraction
- Common validation
- Shared utilities

### Private Helpers (`_function_name` in command files)
**Command-specific** implementation details
- Display functions
- Domain-specific builders
- Orchestration logic

### Formatters (`formatters.py`)
**Generic** formatting utilities
- Timestamps
- Status colors
- Table formatting

### Validators (`validation.py`)
**Input validation** and sanitization
- exp_id, run_id validation
- Path validation
- Token validation

### Output (`output.py`)
**Console output** styling
- info, error, success, warning
- Color management
- Verbosity control

---

**End of Plan**
