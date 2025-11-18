# EPYCloud Command Testing Plan

## Overview

This document outlines a comprehensive testing plan for all epycloud CLI commands. Tests will follow the existing patterns in `tests/integration/test_run_command.py` using pytest fixtures and mocking.

## Current State

- **Total commands**: 8 modules
- **Existing tests**: `run.py` (14 tests), `validation.py` (48 tests)
- **Overall coverage**: 16% (validation module at 97%)

## Phase 1: High Priority Commands (Most Used)

### 1. workflow.py - Cloud Workflows Management

**Purpose**: Manage Cloud Workflows executions (list, describe, cancel, retry)

**Tests to add** (`tests/integration/test_workflow_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_workflow_list_success` | List executions with filtering by status/exp_id |
| `test_workflow_list_with_enrichment` | Fetch execution arguments for display |
| `test_workflow_describe_success` | Get detailed execution info |
| `test_workflow_describe_not_found` | Handle 404 for unknown execution |
| `test_workflow_cancel_running` | Cancel an active workflow |
| `test_workflow_cancel_already_done` | Reject canceling completed workflow |
| `test_workflow_logs_stream` | Stream logs with polling |
| `test_workflow_retry_failed` | Retry with original arguments |
| `test_workflow_api_error_handling` | HTTP errors (404, 401, 500) |

**Mocks required**:
- `requests.get()` / `requests.post()` - Google Cloud Workflows API
- `subprocess.run()` - gcloud logging command
- `get_gcloud_access_token()` - Token fetching
- `time.sleep()` - Polling intervals

**Key functions to test**:
- `_handle_list()`, `_handle_describe()`, `_handle_cancel()`, `_handle_retry()`
- `_enrich_executions_with_arguments()`, `_parse_execution_name()`
- `_parse_timestamp()`, `_display_execution_list()`

---

### 2. logs.py - Pipeline Log Viewing

**Purpose**: View logs from Cloud Batch jobs and workflow executions

**Tests to add** (`tests/integration/test_logs_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_logs_fetch_by_exp_id` | Filter logs by experiment ID |
| `test_logs_fetch_by_stage` | Filter by stage (A/B/C or builder/runner/output) |
| `test_logs_normalize_stage_name` | A→builder, B→runner, C→output conversion |
| `test_logs_follow_mode` | Stream with polling and tail |
| `test_logs_parse_since_time` | Parse duration strings ("1h", "30m", "7d") |
| `test_logs_tail_limit` | Limit log entries (0 = unlimited) |
| `test_logs_empty_result` | Handle no logs found |
| `test_logs_gcloud_error` | Handle gcloud command failure |

**Mocks required**:
- `subprocess.run()` - gcloud logging read command
- `json.loads()` - Parse gcloud JSON output
- `time.sleep()` - Polling interval in stream mode

**Key functions to test**:
- `_fetch_logs()`, `_stream_logs()`, `_display_logs()`
- `_normalize_stage_name()`, `_parse_since_time()`

---

### 3. build.py - Docker Image Management

**Purpose**: Build and manage Docker images for cloud and local deployment

**Tests to add** (`tests/integration/test_build_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_build_cloud_success` | Submit async cloud build |
| `test_build_cloud_with_wait` | Wait for completion |
| `test_build_local_success` | Build and push locally |
| `test_build_dev_success` | Dev build only (no push) |
| `test_build_status_display` | Show active builds |
| `test_build_status_no_builds` | Handle empty build list |
| `test_build_missing_github_pat` | Reject build without PAT |
| `test_build_dry_run` | Show command without executing |
| `test_build_masks_github_pat` | PAT not shown in output |

**Mocks required**:
- `subprocess.run()` - gcloud and docker commands
- `json.loads()` - Parse gcloud output
- `os.chdir()` / `Path.cwd()` - Directory changes
- File I/O for Dockerfile existence checks

**Key functions to test**:
- `_handle_cloud()`, `_handle_local()`, `_handle_dev()`, `_handle_status()`
- `_build_cloud()`, `_build_local()`, `_display_build_status()`

---

## Phase 2: Configuration Commands

### 4. config_cmd.py - Configuration Management

**Purpose**: Manage configuration files and settings

**Tests to add** (`tests/integration/test_config_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_config_init_creates_directory` | Initialize config directory from templates |
| `test_config_init_already_exists` | Handle existing config |
| `test_config_show_displays_config` | Show current configuration |
| `test_config_edit_opens_editor` | Launch $EDITOR |
| `test_config_edit_editor_not_found` | Handle missing editor |
| `test_config_validate_success` | All required fields present |
| `test_config_validate_missing_fields` | Missing project_id/region/bucket |
| `test_config_get_nested_value` | Dot notation access (e.g., `google_cloud.project_id`) |
| `test_config_set_value` | Update config value |
| `test_config_secrets_permissions` | Secrets file has 0600 permissions |

**Mocks required**:
- `subprocess.run()` - Launch editor
- `shutil.copy()` - Template copying
- `yaml.safe_load()` / `yaml.dump()` - YAML operations
- File I/O via `Path` operations

**Key functions to test**:
- `handle_init()`, `handle_show()`, `handle_edit()`, `handle_validate()`
- `handle_get()`, `handle_set()`, `handle_edit_secrets()`

---

### 5. profile.py - Profile Management

**Purpose**: Manage epycloud profiles (independent config sets)

**Tests to add** (`tests/integration/test_profile_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_profile_list_shows_active` | List profiles with * marker for active |
| `test_profile_list_empty` | Handle no profiles |
| `test_profile_use_activates` | Switch to different profile |
| `test_profile_use_not_found` | Handle non-existent profile |
| `test_profile_create_basic` | Create with basic template |
| `test_profile_create_full` | Create with full template |
| `test_profile_delete_success` | Delete inactive profile |
| `test_profile_delete_active_rejected` | Can't delete active profile |
| `test_profile_edit_opens_editor` | Launch editor for profile |
| `test_profile_show_contents` | Display profile YAML |

**Mocks required**:
- File I/O via `Path` operations (glob, read_text, write_text)
- `yaml.safe_load()` / `yaml.dump()` - YAML operations
- `subprocess.run()` - Editor launch

**Key functions to test**:
- `handle_list()`, `handle_use()`, `handle_current()`
- `handle_create()`, `handle_edit()`, `handle_delete()`

---

## Phase 3: Infrastructure Commands

### 6. terraform.py - Infrastructure Management

**Purpose**: Terraform wrapper for GCP infrastructure provisioning

**Tests to add** (`tests/integration/test_terraform_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_terraform_init_success` | Initialize terraform |
| `test_terraform_plan_success` | Plan infrastructure changes |
| `test_terraform_apply_with_auto_approve` | Apply with --yes flag |
| `test_terraform_apply_requires_confirmation` | Confirm in production |
| `test_terraform_destroy_requires_strong_confirmation` | Type project name |
| `test_terraform_output_success` | Show terraform outputs |
| `test_terraform_env_vars_built` | TF_VAR_* variables constructed |
| `test_terraform_dry_run` | Show command without executing |
| `test_terraform_directory_not_found` | Handle missing terraform dir |

**Mocks required**:
- `subprocess.run()` - Terraform commands
- `os.chdir()` / `Path.cwd()` - Directory changes
- `os.environ` - Environment variable access
- Confirmation prompts

**Key functions to test**:
- `_handle_init()`, `_handle_plan()`, `_handle_apply()`, `_handle_destroy()`
- `_handle_output()`, `_get_terraform_env_vars()`

---

### 7. status.py - Pipeline Status Monitoring

**Purpose**: Monitor active workflows and batch jobs

**Tests to add** (`tests/integration/test_status_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_status_show_once` | Display status snapshot |
| `test_status_no_active_jobs` | Handle empty results |
| `test_status_watch_mode` | Auto-refresh with interval |
| `test_status_fetch_active_workflows` | API call for workflows |
| `test_status_fetch_batch_jobs` | gcloud call for batch jobs |
| `test_status_filter_by_exp_id` | Filter results by experiment |
| `test_status_task_count_calculation` | Calculate tasks from batch status |
| `test_status_api_error_resilience` | Continue on transient errors |

**Mocks required**:
- `requests.get()` - Workflow Executions API
- `subprocess.run()` - gcloud batch jobs list
- `json.loads()` - Parse gcloud/API output
- `time.sleep()` - Refresh interval in watch mode
- `get_gcloud_access_token()` - Token fetching

**Key functions to test**:
- `_show_status()`, `_watch_status()`
- `_fetch_active_workflows()`, `_fetch_active_batch_jobs()`
- `_display_status()`

---

### 8. validate.py - Configuration Validation

**Purpose**: Validate experiment configuration locally or from GitHub

**Tests to add** (`tests/integration/test_validate_command.py`):

| Test Name | Description |
|-----------|-------------|
| `test_validate_local_directory` | Validate local config directory |
| `test_validate_local_missing_dir` | Handle non-existent directory |
| `test_validate_remote_github` | Fetch and validate from GitHub |
| `test_validate_github_not_found` | Handle 404 for missing repo/file |
| `test_validate_github_unauthorized` | Handle 401 without PAT |
| `test_validate_missing_basemodel` | Required file check |
| `test_validate_output_text` | Text format output |
| `test_validate_output_json` | JSON format output |
| `test_validate_output_yaml` | YAML format output |

**Mocks required**:
- `requests.get()` - GitHub API calls
- `base64.b64decode()` - Decode GitHub API responses
- `tempfile.TemporaryDirectory()` - Temp file handling
- `yaml.safe_load()` - Parse config files
- `Path.glob()` - Find YAML files

**Key functions to test**:
- `_validate_directory()`, `_validate_remote()`
- `_fetch_config_files()`, `_fetch_github_file()`
- `_display_validation_results()`

---

## Test File Structure

```
tests/integration/
├── test_run_command.py         (existing - 14 tests)
├── test_validation.py          (existing - 48 tests)
├── test_workflow_command.py    (new - ~9 tests)
├── test_logs_command.py        (new - ~8 tests)
├── test_build_command.py       (new - ~9 tests)
├── test_config_command.py      (new - ~10 tests)
├── test_profile_command.py     (new - ~10 tests)
├── test_terraform_command.py   (new - ~9 tests)
├── test_status_command.py      (new - ~8 tests)
└── test_validate_command.py    (new - ~9 tests)
```

**Total new tests**: ~72 tests across 8 command modules

---

## Implementation Priority

1. **Highest**: `workflow.py`, `logs.py` - Most used for monitoring
2. **High**: `build.py` - Critical for deployment
3. **Medium**: `config_cmd.py`, `profile.py` - Setup and configuration
4. **Lower**: `terraform.py`, `status.py`, `validate.py` - Less frequently used

---

## Common Test Patterns

### Mock Config Fixture
```python
@pytest.fixture
def mock_config():
    return {
        "google_cloud": {
            "project_id": "test-project",
            "region": "us-central1",
            "bucket_name": "test-bucket",
        },
        "docker": {...},
        "github": {...},
        "pipeline": {...},
        "resources": {...},
    }
```

### Context Structure
```python
ctx = {
    "config": mock_config,
    "environment": "dev",
    "profile": None,
    "verbose": False,
    "quiet": False,
    "dry_run": False,
    "args": Mock(...),
}
```

### Exit Code Conventions
- `0` - Success
- `1` - Validation/logic error
- `2` - Configuration error

### Mock External Dependencies
```python
@patch("epycloud.commands.workflow.requests.get")
@patch("epycloud.commands.workflow.get_gcloud_access_token")
def test_workflow_list_success(mock_token, mock_get, mock_config):
    mock_token.return_value = "test-token"
    mock_get.return_value = Mock(
        status_code=200,
        json=lambda: {"executions": [...]}
    )
    ...
```

---

## Expected Coverage Improvement

| Module | Current | Target | **Actual** |
|--------|---------|--------|------------|
| run.py | 44% | 60%+ | 44% |
| validation.py | 97% | 97% | - |
| workflow.py | 0% | 50%+ | **66%** ✅ |
| logs.py | 0% | 50%+ | **81%** ✅ |
| build.py | 0% | 50%+ | **77%** ✅ |
| config_cmd.py | 0% | 50%+ | **88%** ✅ |
| profile.py | 0% | 50%+ | **87%** ✅ |
| terraform.py | 0% | 50%+ | **71%** ✅ |
| status.py | 0% | 50%+ | **89%** ✅ |
| validate.py | 0% | 50%+ | 0% (pending) |
| **Overall** | **16%** | **30%+** | **63%** ✅ |

---

## Implementation Progress (as of 2025-11-16)

### ✅ Phase 1 Complete - High Priority Commands

1. **workflow.py** - 25 tests implemented
   - `test_workflow_list_success`, `test_workflow_list_with_status_filter`, `test_workflow_list_with_exp_id_filter`
   - `test_workflow_describe_success`, `test_workflow_describe_not_found`
   - `test_workflow_cancel_success`, `test_workflow_cancel_already_done`, `test_workflow_cancel_dry_run`
   - `test_workflow_retry_success`, `test_workflow_retry_not_found`, `test_workflow_retry_dry_run`
   - `test_workflow_logs_success`, `test_workflow_logs_empty`, `test_workflow_logs_gcloud_error`
   - Helper function tests for timestamp parsing and execution name parsing
   - **Coverage: 66%** (exceeds 50% target)

2. **logs.py** - 30 tests implemented
   - `test_logs_fetch_by_exp_id`, `test_logs_fetch_by_stage`, `test_logs_fetch_by_run_id`
   - `test_logs_fetch_with_task_index`, `test_logs_tail_limit`, `test_logs_tail_unlimited`
   - `test_logs_empty_result`, `test_logs_gcloud_error`, `test_logs_with_severity_filter`
   - `test_normalize_stage_*` (7 tests for A/B/C/builder/runner/output normalization)
   - `test_parse_since_time_*` (4 tests for duration parsing)
   - Follow mode and display formatting tests
   - **Coverage: 81%** (exceeds 50% target)

3. **build.py** - 23 tests implemented
   - `test_build_cloud_success`, `test_build_cloud_with_wait`, `test_build_cloud_dry_run`
   - `test_build_local_success`, `test_build_local_missing_github_pat`, `test_build_local_dry_run`
   - `test_build_dev_success`, `test_build_dev_missing_github_pat`, `test_build_dev_with_custom_tag`
   - `test_build_status_display`, `test_build_status_no_builds`, `test_build_status_ongoing_only`
   - Error handling and validation tests
   - **Coverage: 77%** (exceeds 50% target)

### ✅ Phase 2 Complete - Configuration Commands

4. **config_cmd.py** - 31 tests implemented
   - `test_config_init_*` (3 tests for directory creation, skip existing, default profile)
   - `test_config_show_*` (4 tests for display, raw YAML, metadata, missing config)
   - `test_config_edit_*` (5 tests for editor, env file, not found, editor errors)
   - `test_config_edit_secrets_*` (3 tests for editor, create missing, fix permissions)
   - `test_config_validate_*` (4 tests for success, missing fields, warnings, load error)
   - `test_config_get_*` (3 tests for nested values, key not found, top-level)
   - `test_config_set_*` (3 tests for set value, file not found, nested key)
   - `test_config_list_envs_*` (3 tests for list, current marker, empty)
   - No subcommand and unknown subcommand tests
   - **Coverage: 88%** (exceeds 50% target)

5. **profile.py** - 23 tests implemented
   - `test_profile_list_*` (4 tests for list, mark active, no directory, empty)
   - `test_profile_use_*` (2 tests for activate, not found)
   - `test_profile_current_*` (2 tests for show active, no active)
   - `test_profile_create_*` (4 tests for basic, full, already exists, default values)
   - `test_profile_edit_*` (4 tests for editor, not found, editor errors)
   - `test_profile_show_*` (2 tests for contents, not found)
   - `test_profile_delete_*` (3 tests for success, active rejected, not found)
   - No subcommand and unknown subcommand tests
   - **Coverage: 87%** (exceeds 50% target)

### ✅ Phase 3 Complete - Infrastructure Commands

6. **terraform.py** - 25 tests implemented
   - `test_terraform_init_*` (5 tests for success, directory not found, dry run, command not found, failure)
   - `test_terraform_plan_*` (3 tests for success, target resource, dry run)
   - `test_terraform_apply_*` (4 tests for auto-approve, prod confirmation, cancelled, dry run)
   - `test_terraform_destroy_*` (4 tests for confirmation, auto-approve, cancelled, dry run)
   - `test_terraform_output_*` (3 tests for success, specific name, dry run)
   - `test_get_terraform_env_vars_*` (3 tests for basic, batch config, partial config)
   - No subcommand, unknown subcommand, missing config tests
   - **Coverage: 71%** (exceeds 50% target)

7. **status.py** - 22 tests implemented
   - `test_status_show_*` (5 tests for once, no active, with workflows, with jobs, filter)
   - `test_fetch_active_workflows_*` (4 tests for success, filter, empty, API error)
   - `test_fetch_active_batch_jobs_*` (4 tests for success, empty, filter, gcloud error)
   - `test_display_status_*` (6 tests for empty, workflows, jobs, filter, invalid JSON, missing task groups)
   - Watch mode interrupt test
   - Missing config and project_id tests
   - **Coverage: 89%** (exceeds 50% target)

### Infrastructure Updates

- Updated `tests/conftest.py` to add missing github config keys:
  - `github.modeling_suite_repo`
  - `github.modeling_suite_ref`

### Test Statistics

- **New tests added**: 179 (78 Phase 1 + 54 Phase 2 + 47 Phase 3)
- **Total integration tests**: 227
- **Commands module coverage**: 63% (up from 16%)

---

## Next Steps

1. ~~Start with `workflow.py` tests (most complex API interactions)~~ ✅ Done
2. ~~Add `logs.py` tests (pairs with workflow monitoring)~~ ✅ Done
3. ~~Add `build.py` tests (critical for deployment pipeline)~~ ✅ Done
4. ~~Continue with remaining commands in priority order (Phase 2-3)~~ ✅ Done
5. ~~Run coverage report after each module~~ ✅ Done
6. ~~Update fixtures as needed for shared patterns~~ ✅ Done
7. Add `validate.py` tests (optional, lower priority)
8. Improve coverage for `run.py` (currently 44%)
9. Consider end-to-end integration tests with actual GCP services (optional)
