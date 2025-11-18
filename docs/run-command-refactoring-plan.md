# Run Command Refactoring Plan

**Date:** 2025-11-15
**File:** `src/epycloud/commands/run.py` (1,227 lines)
**Goal:** Fix DRY violations and extract functions without over-engineering

---

## Executive Summary

**Current State:**
- File is functionally correct and production-ready
- Contains 4 execution paths with code duplication
- Main issue: Configuration extraction repeated 4 times (~80 lines of duplication)

**Recommendation:**
- Implement **minimal, high-value refactorings only**
- Focus on genuine DRY violations that cause maintenance burden
- Avoid over-engineering (no complex class hierarchies, no excessive abstractions)

**Expected Outcome:**
- Save ~45 lines of code
- Centralize configuration extraction
- Improve maintainability
- Implementation time: 30-45 minutes
- Risk: LOW

---

## Code Review Findings

### Strengths
- ✅ Clear, linear flow (easy to follow)
- ✅ Good error handling
- ✅ Comprehensive confirmation prompts
- ✅ Well-structured argument parsing
- ✅ Robust validation

### Critical DRY Violations

#### 1. Configuration Extraction (Repeated 4x)
**Lines:** 364-377, 568-573, 740-749, 952-957
**Impact:** HIGH - Any config field change requires updating 4 functions
**Lines of duplication:** ~80 lines total

#### 2. Image URI Construction (Repeated 2x)
**Lines:** 391-395, 752-756
**Impact:** MEDIUM - Image URI format changes in 2 places
**Lines of duplication:** ~10 lines total

#### 3. Input Validation (Repeated 2x)
**Lines:** 214-219, 283-288
**Impact:** MEDIUM - Validation logic duplicated
**Lines of duplication:** ~12 lines total

#### 4. Stage Name Normalization (Repeated 2x)
**Lines:** 274-280, 1114
**Impact:** LOW - Simple mapping logic
**Lines of duplication:** ~8 lines total

### What's Actually Fine (No Changes Needed)

- **Confirmation info dictionaries** (lines 406-424, 583-593, 783-800, 967-982)
  - Each context builds different fields
  - Extraction would add complexity without benefit

- **Long functions** (200+ lines)
  - Actually quite readable
  - Linear flow, no crazy nesting
  - Each has unique orchestration logic

- **Already well-extracted helpers:**
  - `_build_env_from_config()` (lines 885-919)
  - `_run_docker_compose_stage()` (lines 1038-1074)
  - `_build_batch_job_config()` (lines 1077-1186)
  - `_generate_run_id()` (lines 1216-1226)
  - `_get_batch_sa_email()` (lines 1189-1213)

---

## Refactoring Plan

### Priority 1: Extract Config Values Function ⭐ CRITICAL

**Problem:** Configuration extraction repeated in 4 functions

**Current Code (repeated 4x):**
```python
google_cloud_config = config.get("google_cloud", {})
github_config = config.get("github", {})
pipeline_config = config.get("pipeline", {})
docker_config = config.get("docker", {})
batch_config = google_cloud_config.get("batch", {})

project_id = google_cloud_config.get("project_id")
region = google_cloud_config.get("region", "us-central1")
bucket_name = google_cloud_config.get("bucket_name")
dir_prefix = pipeline_config.get("dir_prefix", "pipeline/flu/")
# ... etc
```

**Proposed Solution:**
```python
def _extract_config_values(config: dict[str, Any]) -> dict[str, Any]:
    """Extract commonly used configuration values.

    Returns a flat dict with all commonly accessed config values.
    This eliminates repetitive config extraction across functions.

    Args:
        config: Full configuration dict

    Returns:
        Flat dict with extracted values
    """
    google_cloud = config.get("google_cloud", {})
    github = config.get("github", {})
    pipeline = config.get("pipeline", {})
    docker = config.get("docker", {})
    batch = google_cloud.get("batch", {})

    return {
        # Google Cloud
        "project_id": google_cloud.get("project_id"),
        "region": google_cloud.get("region", "us-central1"),
        "bucket_name": google_cloud.get("bucket_name"),

        # Docker
        "registry": docker.get("registry", "us-central1-docker.pkg.dev"),
        "repo_name": docker.get("repo_name", "epymodelingsuite-repo"),
        "image_name": docker.get("image_name", "epymodelingsuite"),
        "image_tag": docker.get("image_tag", "latest"),

        # GitHub
        "github_forecast_repo": github.get("forecast_repo", ""),
        "github_modeling_suite_repo": github.get("modeling_suite_repo", ""),
        "github_modeling_suite_ref": github.get("modeling_suite_ref", "main"),
        "github_pat": github.get("personal_access_token", ""),

        # Pipeline
        "dir_prefix": pipeline.get("dir_prefix", "pipeline/flu/"),
        "max_parallelism": pipeline.get("max_parallelism", 100),

        # Batch (full config for stage-specific access)
        "batch_config": batch,
    }
```

**Usage in functions:**
```python
# Before (20 lines):
google_cloud_config = config.get("google_cloud", {})
github_config = config.get("github", {})
pipeline_config = config.get("pipeline", {})
docker_config = config.get("docker", {})
# ... 15 more lines

# After (2 lines):
cfg = _extract_config_values(config)
project_id = cfg["project_id"]
```

**Impact:**
- Lines saved: ~35 lines (80 → 45)
- Maintenance benefit: **HIGH** - Config changes in ONE place
- Risk: **LOW** - Pure extraction, no logic change
- Functions affected: 4 (`_run_workflow_cloud`, `_run_workflow_local`, `_run_job_cloud`, `_run_job_local`)

---

### Priority 2: Extract Image URI Builder ⭐ HIGH

**Problem:** Docker image URI construction duplicated 2x

**Current Code (repeated 2x):**
```python
registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
image_name = docker_config.get("image_name", "epymodelingsuite")
image_tag = docker_config.get("image_tag", "latest")
image_uri = f"{registry}/{project_id}/{repo_name}/{image_name}:{image_tag}"
```

**Proposed Solution:**
```python
def _build_image_uri(cfg: dict[str, Any]) -> str:
    """Build Docker image URI from config values.

    Args:
        cfg: Dict from _extract_config_values()

    Returns:
        Full image URI (e.g., "us-central1-docker.pkg.dev/project/repo/image:tag")
    """
    return (
        f"{cfg['registry']}/"
        f"{cfg['project_id']}/"
        f"{cfg['repo_name']}/"
        f"{cfg['image_name']}:{cfg['image_tag']}"
    )
```

**Usage:**
```python
# Before (5 lines):
registry = docker_config.get("registry", "us-central1-docker.pkg.dev")
repo_name = docker_config.get("repo_name", "epymodelingsuite-repo")
image_name = docker_config.get("image_name", "epymodelingsuite")
image_tag = docker_config.get("image_tag", "latest")
image_uri = f"{registry}/{project_id}/{repo_name}/{image_name}:{image_tag}"

# After (1 line):
image_uri = _build_image_uri(cfg)
```

**Impact:**
- Lines saved: ~4 lines (10 → 6)
- Maintenance benefit: **MEDIUM** - URI format centralized
- Risk: **LOW** - Simple string formatting
- Functions affected: 2 (`_run_workflow_cloud`, `_run_job_cloud`)
- **Note:** Can be integrated into Priority 1's function

---

### Priority 3: Extract Input Validation ⭐ MEDIUM

**Problem:** Validation pattern duplicated 2x

**Current Code (repeated 2x):**
```python
try:
    exp_id = validate_exp_id(args.exp_id)
    run_id = validate_run_id(args.run_id) if args.run_id else None
except ValidationError as e:
    error(str(e))
    return 1
```

**Proposed Solution:**
```python
def _validate_inputs(args: argparse.Namespace) -> tuple[str, str | None] | None:
    """Validate exp_id and run_id from args.

    Args:
        args: Parsed command-line arguments

    Returns:
        Tuple of (exp_id, run_id) on success, None on failure (error already printed)
    """
    try:
        exp_id = validate_exp_id(args.exp_id)
        run_id = validate_run_id(args.run_id) if args.run_id else None
        return exp_id, run_id
    except ValidationError as e:
        error(str(e))
        return None
```

**Usage:**
```python
# Before (6 lines):
try:
    exp_id = validate_exp_id(args.exp_id)
    run_id = validate_run_id(args.run_id) if args.run_id else None
except ValidationError as e:
    error(str(e))
    return 1

# After (4 lines):
validated = _validate_inputs(args)
if validated is None:
    return 1
exp_id, run_id = validated
```

**Impact:**
- Lines saved: ~4 lines (12 → 8)
- Maintenance benefit: **MEDIUM** - Validation logic centralized
- Risk: **LOW** - Simple extraction with error handling
- Functions affected: 2 (`_handle_workflow`, `_handle_job`)

---

### Priority 4: Extract Stage Name Normalization (Optional)

**Problem:** Stage name mapping duplicated 2x

**Current Code:**
```python
# In _handle_job (lines 274-280):
stage = args.stage.upper()
if stage == "BUILDER":
    stage = "A"
elif stage == "RUNNER":
    stage = "B"
elif stage == "OUTPUT":
    stage = "C"

# In _build_batch_job_config (line 1114):
stage_name = {"A": "builder", "B": "runner", "C": "output"}[stage]
```

**Proposed Solution:**
```python
def _normalize_stage_name(stage: str) -> str:
    """Normalize stage name to single letter (A, B, or C).

    Args:
        stage: Stage name (A/B/C/builder/runner/output, case-insensitive)

    Returns:
        Normalized stage letter (A, B, or C)
    """
    stage_upper = stage.upper()
    if stage_upper in ("A", "B", "C"):
        return stage_upper

    mapping = {"BUILDER": "A", "RUNNER": "B", "OUTPUT": "C"}
    return mapping.get(stage_upper, stage_upper)


def _stage_letter_to_name(stage: str) -> str:
    """Convert stage letter to full name.

    Args:
        stage: Stage letter (A, B, or C)

    Returns:
        Stage name (builder, runner, or output)
    """
    return {"A": "builder", "B": "runner", "C": "output"}[stage]
```

**Usage:**
```python
# In _handle_job:
# Before (7 lines):
stage = args.stage.upper()
if stage == "BUILDER":
    stage = "A"
elif stage == "RUNNER":
    stage = "B"
elif stage == "OUTPUT":
    stage = "C"

# After (1 line):
stage = _normalize_stage_name(args.stage)

# In _build_batch_job_config:
# Before (1 line):
stage_name = {"A": "builder", "B": "runner", "C": "output"}[stage]

# After (1 line):
stage_name = _stage_letter_to_name(stage)
```

**Impact:**
- Lines saved: ~2 lines (8 → 6, accounting for new functions)
- Maintenance benefit: **LOW-MEDIUM** - Stage mapping centralized
- Risk: **LOW** - Simple string mapping
- Functions affected: 2 (`_handle_job`, `_build_batch_job_config`)
- **Note:** Optional - minimal benefit, but improves clarity

---

## Summary Table

| Priority | Refactoring | Lines Before | Lines After | Saved | Benefit | Risk | Time |
|----------|-------------|--------------|-------------|-------|---------|------|------|
| **1** | Config extraction | ~80 (4×20) | ~45 (func + 4×5) | ~35 | **HIGH** | **LOW** | 15-20 min |
| **2** | Image URI builder | ~10 (2×5) | ~6 (func + 2×1) | ~4 | **MEDIUM** | **LOW** | 5 min |
| **3** | Input validation | ~12 (2×6) | ~8 (func + 2×2) | ~4 | **MEDIUM** | **LOW** | 10 min |
| **4** | Stage normalization | ~8 | ~6 (funcs + usage) | ~2 | **LOW** | **LOW** | 10 min |
| **TOTAL** | - | **~110** | **~65** | **~45** | - | - | **30-45 min** |

---

## Implementation Plan

### Step 1: Add Helper Functions
Add these functions after line 1227 (end of file, before existing helpers):

1. `_extract_config_values(config)` - ~25 lines
2. `_build_image_uri(cfg)` - ~8 lines (or integrate into #1)
3. `_validate_inputs(args)` - ~10 lines
4. `_normalize_stage_name(stage)` - ~10 lines (optional)
5. `_stage_letter_to_name(stage)` - ~5 lines (optional)

### Step 2: Update Call Sites (One at a Time)

**Priority 1 - Config extraction:**
1. Update `_run_workflow_cloud()` (lines 364-395)
2. Update `_run_workflow_local()` (lines 568-573)
3. Update `_run_job_cloud()` (lines 740-756)
4. Update `_run_job_local()` (lines 952-957)

**Priority 2 - Image URI:**
1. Update `_run_workflow_cloud()` (lines 391-395)
2. Update `_run_job_cloud()` (lines 752-756)

**Priority 3 - Validation:**
1. Update `_handle_workflow()` (lines 214-219)
2. Update `_handle_job()` (lines 283-288)

**Priority 4 - Stage normalization (optional):**
1. Update `_handle_job()` (lines 274-280)
2. Update `_build_batch_job_config()` (line 1114)

### Step 3: Test Each Change
After each priority:
```bash
# Quick verification with dry-run
uv run epycloud run workflow --exp-id test --dry-run --yes
uv run epycloud run job --stage A --exp-id test --dry-run --yes
```

---

## What NOT to Change

### 1. Confirmation Info Dictionaries
**Lines:** 406-424, 583-593, 783-800, 967-982

**Why NOT extract:**
- Each context builds **different fields**
- Cloud vs. Local have different data
- Workflow vs. Job have different requirements
- Extraction would require complex conditional logic
- **Result would be MORE complex than current code**

**Verdict:** SKIP - Apparent duplication is actually context-specific data

### 2. Already Well-Extracted Functions
- `_build_env_from_config()` - Single purpose, well-contained
- `_run_docker_compose_stage()` - Clear responsibility
- `_build_batch_job_config()` - Complex but cohesive
- `_generate_run_id()` - Perfect as-is
- `_get_batch_sa_email()` - Already extracted

### 3. Long Functions (200+ lines)
- `_run_workflow_cloud()` (207 lines)
- `_run_workflow_local()` (164 lines)
- `_run_job_cloud()` (175 lines)

**Why NOT break up:**
- Linear flow (easy to follow top-to-bottom)
- Each has unique orchestration logic
- No excessive nesting
- Breaking up would create artificial boundaries

---

## Final Recommendations

### Do This (Priorities 1-3)
✅ **Implement config extraction** - Fixes genuine DRY violation, high maintenance benefit
✅ **Implement image URI builder** - Simple, clear benefit
✅ **Implement input validation** - Centralizes validation logic
❓ **Consider stage normalization** - Optional, minimal benefit but improves clarity

### Don't Do This
❌ **Don't extract confirmation info** - Would add complexity
❌ **Don't break up long functions** - They're actually readable
❌ **Don't create complex class hierarchies** - Over-engineering
❌ **Don't use TypedDict for config** - Adds type complexity without benefit
❌ **Don't create runner classes** - Academic, not practical

---

## Expected Outcome

**Before:**
- 1,227 lines
- Config extraction in 4 places
- Image URI construction in 2 places
- Validation in 2 places

**After:**
- ~1,182 lines (45 lines saved)
- Config extraction in 1 place
- Image URI construction in 1 place
- Validation in 1 place
- 4-5 new helper functions (well-named, single-purpose)

**Benefits:**
- Easier to add new config fields
- Easier to change image URI format
- Centralized validation logic
- No loss of readability
- Low risk of bugs

**Time Investment:** 30-45 minutes
**Maintenance ROI:** High - Will pay off on first config change

---

## Code Review Conclusion

The code is **functionally excellent** but has **genuine DRY violations** that should be fixed. The proposed refactoring is **minimal and targeted** - it fixes real problems without over-engineering.

This is NOT a case of "refactor because the file is long" or "refactor to match textbook architecture." This is pragmatic refactoring to eliminate actual duplication that causes maintenance burden.

**Recommendation:** Proceed with Priorities 1-3, skip Priority 4 unless you find it valuable.
