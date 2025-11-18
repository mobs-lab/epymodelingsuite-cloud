# Implementation Decisions

**Original Date:** 2025-11-06
**Update Date:** 2025-11-14
**Status:** Implemented and In Production

---

## Summary

Final decisions for the `epycloud` CLI tool implementation.

---

## Key Decisions

### 1. Package Name

**Decision:** `epycloud`

**Rationale:**
- Short, memorable command name
- Easy to type
- Clear what it's for (epidemic modeling cloud)

**Details:**
- Repository name: `epymodelingsuite-cloud` (existing, no change)
- Python package name: `epycloud` (installable package)
- CLI command: `epycloud` (after `pip install`)

```bash
# Repository
git clone https://github.com/mobs-lab/epymodelingsuite-cloud

# Package installation
cd epymodelingsuite-cloud
pip install -e .

# Command usage
epycloud --version
epycloud run workflow --exp-id flu-2024
```

---

### 2. Config Directory

**Decision:** `~/.config/epymodelingsuite-cloud/`

**Rationale:**
- Follows XDG Base Directory specification
- Standard on Linux and macOS
- Separates config from cache and data
- Consistent with other professional tools

**Directory Structure:**
```
~/.config/epymodelingsuite-cloud/     # XDG_CONFIG_HOME
├── config.yaml
├── secrets.yaml
├── active_profile
├── environments/
│   ├── dev.yaml
│   ├── prod.yaml
│   └── local.yaml
└── profiles/
    ├── flu.yaml
    ├── covid.yaml
    └── rsv.yaml

~/.local/share/epymodelingsuite-cloud/  # XDG_DATA_HOME
└── cache/

~/.cache/epymodelingsuite-cloud/        # XDG_CACHE_HOME
└── build-cache/
```

**Alternative considered:** `~/.epycloud/`
- Shorter path
- But doesn't follow XDG standard
- Rejected in favor of standards compliance

---

### 3. Profile Support

**Decision:** Full profile support

**Features:**
- Profiles for different diseases/projects (flu, covid, rsv, etc.)
- Conda-style activation: `epycloud profile use flu`
- Profile-specific settings (forecast repo, resources, etc.)
- Store in `~/.config/epymodelingsuite-cloud/profiles/`

**Profile Commands:**
```bash
epycloud profile list                  # List all profiles
epycloud profile use flu               # Activate profile
epycloud profile current               # Show active profile
epycloud profile create mpox           # Create new profile
epycloud profile edit flu              # Edit profile
epycloud profile show flu              # Show profile config
epycloud profile delete old-project    # Delete profile
```

**Why profiles?**
- Natural workflow: work on one disease at a time
- Convenient: don't repeat `--profile` on every command
- Flexible: can override with `--profile` flag
- Organized: separate config per project/disease

---

### 4. Bash/Zsh Completion

**Decision:** Include completion scripts

**Implementation:**
- Generate completion scripts from argparse
- Support both bash and zsh
- Install command: `epycloud completion bash > /etc/bash_completion.d/epycloud`

**Features:**
```bash
# Install bash completion
epycloud completion bash > ~/.bash_completion.d/epycloud

# Install zsh completion
epycloud completion zsh > ~/.zsh/completion/_epycloud

# After installation:
epycloud <TAB>         # Shows: build, run, workflow, config, ...
epycloud run <TAB>     # Shows: workflow, job
epycloud --env <TAB>   # Shows: dev, prod, local
```

**Why?**
- Improves usability significantly
- Standard feature for modern CLI tools
- Reduces typing errors
- Helps with discovery of commands/options

**Implementation approach:**
- Use `argcomplete` library (optional dependency)
- Or generate static completion files
- Fallback gracefully if not installed

---

### 5. Distribution

**Decision:** Use `uv tool install` for isolated CLI installation

**Current (Phase 1):**
- Distribute via GitHub repository
- **Recommended:** `uv tool install /path/to/epymodelingsuite-cloud`
- Alternative: `uv tool install git+https://github.com/mobs-lab/epymodelingsuite-cloud.git`
- Development: `uv sync` for virtual environment

**Future (Phase 2):**
- Publish to PyPI when stable
- Install with: `uv tool install epycloud`
- Version management with semantic versioning
- Changelog and release notes

**Why `uv tool install`?**
- Isolated environment - doesn't pollute user's Python installation
- No dependency conflicts with other tools
- Fast installation and resolution
- Modern Python tooling standard
- Easy global CLI access without environment activation

**Why GitHub first?**
- Internal tool for research team
- Rapid iteration during development
- No need for public distribution yet
- Can publish to PyPI later when mature

**Installation methods:**
```bash
# Recommended: Isolated CLI tool
uv tool install /path/to/epymodelingsuite-cloud

# Development: Virtual environment
cd epymodelingsuite-cloud
uv sync
uv run epycloud --version

# Future: From PyPI
uv tool install epycloud
```

---

## Configuration Decisions

### Environment vs Profile

**Environment (dev/prod/local):**
- CLI argument: `epycloud --env=prod`
- Explicit and visible
- Infrastructure/deployment target
- Safety: can't accidentally run in prod

**Profile (flu/covid/rsv):**
- Conda-style activation: `epycloud profile use flu`
- Stateful (persists between commands)
- Project/disease configuration
- Convenience: don't repeat on every command

### Config Structure

**Top-level sections:**
```yaml
storage:                # Universal (local + cloud)
  dir_prefix: "pipeline/{environment}/{profile}"

google_cloud:           # GCP-specific
  project_id: ...
  region: ...
  bucket_name: ...
  batch:                # Cloud Batch settings
    max_parallelism: ...
    stage_a/b/c: ...

docker:                 # Docker images
  repo_name: ...
  image_name: ...
  image_tag: ...

github:                 # GitHub repositories
  modeling_suite_repo: ...
  modeling_suite_ref: ...
  # forecast_repo is profile-specific

logging:                # Application logging
  level: ...
  storage_verbose: ...

workflow:               # Workflow orchestration
  retry_policy: ...
  notification: ...
```

---

## Technical Decisions

### Language

**Decision:** Python (not Go)

**Rationale:**
- Same language as pipeline scripts
- Team familiarity
- Reuse existing code (storage, config, logging)
- Faster development
- CLI is a wrapper, not the bottleneck

### Python Package Structure

**Decision:** Modern package structure with `src/` layout

```
epymodelingsuite-cloud/
├── pyproject.toml              # Modern packaging
├── src/
│   └── epycloud/               # Installable package
│       ├── __init__.py
│       ├── cli.py
│       ├── config/
│       ├── commands/
│       ├── lib/
│       └── utils/
├── scripts/                    # Pipeline scripts (not CLI)
├── docker/
├── terraform/
└── tests/
```

**Why `src/` layout?**
- Prevents accidental imports from source tree
- Forces testing of installed package
- Industry best practice
- Clear separation of installable vs. non-installable code

### CLI Framework

**Decision:** Python stdlib `argparse` (not click/typer)

**Rationale:**
- Zero new dependencies
- Good enough for our needs
- Team knows it
- Reduces complexity

**What we get:**
- Subcommands
- Type validation
- Help generation
- Argument parsing

**What we sacrifice:**
- Slightly more boilerplate vs click
- Acceptable tradeoff for zero dependencies

### Config Format

**Decision:** YAML (not TOML/JSON)

**Rationale:**
- Already using PyYAML in dependencies
- Better for nested structures
- More human-readable
- Supports comments
- Industry standard for config files

---

## Implementation Phases

### Phase 1: Core Package & Config (Week 1) ✅ COMPLETED
- [x] Package structure (`src/epycloud/`)
- [x] `pyproject.toml`
- [x] Config system with XDG paths
- [x] Config loading and merging (env + profile)
- [x] Basic CLI framework with argparse
- [x] `config` command (init/show/validate/path/get/set/edit)
- [x] `profile` command (use/list/create/show/edit/delete/current)

**Status:** Phase 1 completed on 2025-11-06. All core infrastructure is functional.

### Phase 2: Essential Commands (Week 2) ✅ COMPLETED
- [x] `build` commands (cloud/local/dev)
- [x] `run` commands (workflow/job)
- [x] `workflow` commands (list/describe/logs/cancel/retry)
- [x] `terraform` commands (init/plan/apply/destroy/output)

**Status:** Phase 2 completed on 2025-11-07. All essential commands are functional.

### Phase 3: Monitoring & Verification (Week 3) ✅ COMPLETED
- [x] `validate` command (GitHub API + local path validation)
- [x] `status` command (monitoring/watch mode)
- [x] `logs` command (Cloud Logging integration)

**Status:** Phase 3 completed on 2025-11-07. All monitoring and verification commands are functional.

### Phase 4: Polish & Documentation (Week 4)
- [ ] Bash/zsh completion scripts
- [ ] Complete documentation
- [ ] Migration guide for users
- [ ] Integration tests
- [ ] v0.1.0 release

### Phase 5: Low Priority Features (Future)
- [ ] `download` command (download results from GCS)
- [ ] `list` command (list experiments/runs/outputs)
- [ ] Performance optimizations
- [ ] Advanced error recovery

### Future: PyPI Distribution
- [ ] Semantic versioning
- [ ] Changelog automation
- [ ] PyPI publishing
- [ ] CI/CD for releases

---

## File Structure Summary

```
Repository: epymodelingsuite-cloud/
├── src/epycloud/                                  # Python package
├── ~/.config/epymodelingsuite-cloud/              # User config
├── ~/.local/share/epymodelingsuite-cloud/         # User data
└── ~/.cache/epymodelingsuite-cloud/               # Cache

Command: epycloud
Installation: pip install -e .
```

---

## Scope Decisions

### MVP Commands (Phase 1-3) ✅ COMPLETE
**Essential for initial release:**
- ✅ `config` - Configuration management (Phase 1)
- ✅ `profile` - Profile management (flu/covid/rsv) (Phase 1)
- ✅ `build` - Docker image building (Phase 2)
- ✅ `run` - Execute pipeline stages/workflows (Phase 2)
- ✅ `workflow` - Workflow management (Phase 2)
- ✅ `terraform` (alias: `tf`) - Infrastructure management (Phase 2)
- ✅ `validate` - Experiment validation (prevent costly mistakes) (Phase 3)
- ✅ `status` - Pipeline status monitoring (Phase 3)
- ✅ `logs` - Log viewing (Phase 3)

### Low Priority Commands (Phase 5)
**Deferred to future releases:**
- 📦 `download` - Download results from GCS (users can use `gsutil`)
- 📦 `list` - List experiments/runs (workflow/status cover most needs)

### Excluded Commands
**Not implementing:**
- ❌ `cost` - Cost estimation (complex, use GCP console)
- ❌ `init` - Project initialization (manual `epycloud.yaml` creation is fine)

### Rationale
- **MVP focus:** Core workflow (build → verify → run → monitor)
- **User workarounds:** `gsutil` for downloads, GCP console for cost tracking
- **Reduced complexity:** 9 commands instead of 12
- **Faster delivery:** Ship useful tool sooner, add features based on feedback

## Code Quality Standards

### Docstring Style

**Decision:** NumPy-style docstrings

**Rationale:**
- Industry standard for scientific Python projects
- Better readability for complex functions
- Consistent with numpy, scipy, pandas style
- Supported by Sphinx documentation generators
- Clear parameter and return type documentation

**Example:**
```python
def validate_config(config_path, github_token=None):
    """
    Validate experiment configuration files.

    Parameters
    ----------
    config_path : str or Path
        Path to config directory containing YAML files.
    github_token : str, optional
        GitHub personal access token for remote validation.
        Default is None (uses token from config/env).

    Returns
    -------
    dict
        Validation result with 'status' and 'errors' keys.

    Raises
    ------
    ConfigError
        If config directory does not exist or is invalid.
    ValidationError
        If configuration fails validation checks.

    Examples
    --------
    >>> result = validate_config('./config')
    >>> result['status']
    'pass'
    """
    pass
```

**Reference:** [NumPy Documentation Guide](https://numpydoc.readthedocs.io/en/latest/format.html)

### Code Formatting and Linting

**Decision:** Use `ruff` for all Python code

**Rationale:**
- Fast Rust-based linter/formatter (100x faster than black+flake8)
- Replaces multiple tools (black, isort, flake8, pylint)
- Zero configuration needed for sensible defaults
- Auto-fix capabilities
- Modern Python tooling standard

**Workflow:**
1. Edit Python files
2. Run `ruff check --fix` to auto-fix issues
3. Run `ruff format` to format code
4. Commit changes

**Commands:**
```bash
# Check and auto-fix issues
ruff check --fix src/epycloud/

# Format code
ruff format src/epycloud/

# Combined workflow (check + format)
ruff check --fix src/epycloud/ && ruff format src/epycloud/

# Check specific file
ruff check src/epycloud/cli.py
```

**Configuration (pyproject.toml):**
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**When to run:**
- After editing any Python file
- Before committing changes
- As part of CI/CD pipeline (future)
- Integrated with pre-commit hooks (future)

---

## Open Questions (Resolved)

1. ✅ Package name: `epycloud`
2. ✅ Config directory: `~/.config/epymodelingsuite-cloud/`
3. ✅ Profile support: Yes, full support with conda-style activation
4. ✅ Bash/zsh completion: Yes, include
5. ✅ Distribution: GitHub now, PyPI later
6. ✅ Command scope: 9 essential commands for MVP
7. ✅ Docstring style: NumPy-style docstrings
8. ✅ Linting/formatting: ruff for all Python code

---

## Next Steps

1. Create package structure
2. Implement config system
3. Build CLI framework
4. Implement commands
5. Add completion scripts
6. Write documentation
7. Test and iterate

---

## Implementation Log

### 2025-11-06: Phase 1 - Core Package & Config System
**Completed:** Package structure, config system, profile management

**Commands Implemented:**
- `config` - Configuration management (init, show, edit, validate, get, set, path)
- `profile` - Profile management (use, list, create, show, edit, delete, current)

**Commits:**
- `014e0a0` - Implement Phase 1: Core package and configuration system

---

### 2025-11-06: Build Command
**Implemented:** `epycloud build` with cloud/local/dev modes

**Key Features:**
- Cloud Build (async/sync), local build+push, dev build
- Flags: `--no-cache`, `--tag`, `--push`, `--wait`
- GitHub PAT masking, config validation, colored output

**Commit:** `248d5f1` - Implement build command with cloud/local/dev modes

---

### 2025-11-06: Run Command
**Implemented:** `epycloud run` with workflow and job subcommands

**Key Features:**
- `run workflow` - Submit complete pipeline (A→B→C) to Cloud Workflows or run locally
- `run job` - Run individual stages (A/B/C) on Cloud Batch or locally
- Auto-generated run IDs, Cloud Workflows REST API integration
- Cloud Batch job configuration, docker compose integration

**Commit:** `317ff8b` - Implement run command with workflow and job subcommands

---

### 2025-11-07: Workflow Command
**Implemented:** `epycloud workflow` with five subcommands

**Subcommands:**
- `list` - List executions with filters (status, exp-id, since, limit)
- `describe` - Show execution details (status, timestamps, args, errors)
- `logs` - Stream logs with `--follow` and `--tail` options
- `cancel` - Cancel running execution
- `retry` - Retry failed execution with same parameters

**Key Features:**
- Cloud Workflows REST API integration, Cloud Logging integration
- Color-coded output, timestamp parsing, duration calculation
- No external dependencies beyond stdlib

**Commit:** `68bb27e` - Implement workflow command with list/describe/logs/cancel/retry subcommands

---

### 2025-11-07: Terraform Command
**Implemented:** `epycloud terraform` (alias: `tf`) with five subcommands

**Subcommands:**
- `init` - Initialize Terraform backend and providers
- `plan` - Preview infrastructure changes
- `apply` - Apply infrastructure changes with optional --auto-approve
- `destroy` - Destroy infrastructure with confirmation prompt
- `output` - Show Terraform outputs (all or specific)

**Key Features:**
- TF_VAR_* environment variable mapping from config (google_cloud, docker, batch stages)
- Confirmation prompts for production environment
- Target resource support (--target flag)
- Dry-run mode support
- Works from terraform/ directory in project root
- Passes through all terraform exit codes

**Commit:** `56dfd9c` - Implement terraform command with init/plan/apply/destroy/output subcommands

---

### 2025-11-07: Validate Command
**Implemented:** `epycloud validate` for experiment configuration validation

**Key Features:**
- Two validation modes: remote (GitHub) or local (filesystem)
- Remote: `--exp-id` fetches from GitHub forecast repository using API
- Local: `--path` validates local config directory
- Validates config sets: basemodel + modelset (sampling/calibration) + optional output
- Uses epymodelingsuite functions directly (identify_config_type, load_*_config_from_file)
- Validates cross-config consistency with validate_cross_config_consistency
- Multiple output formats (text, json, yaml)
- Support for GitHub token from config/secrets/env

**Validation Process:**
1. Remote mode: Fetch all YAML files from GitHub (experiments/{exp_id}/config/)
2. Local mode: Read all YAML files from provided path
3. Classify configs using identify_config_type (basemodel, sampling, calibration, output)
4. Load configs using appropriate loader functions
5. Validate cross-config consistency
6. Typically validates one config set per experiment (1 basemodel + 1 modelset + optional output)

**Implementation Pattern:**
Based on forecast repo GitHub Actions validation script:
- Find and classify YAML files by type
- Load configs with epymodelingsuite.config_loader functions
- Validate consistency using epymodelingsuite.schema.general.validate_cross_config_consistency
- Report pass/fail for the config set

**Usage:**
- `epycloud validate --exp-id test-sim` (remote from GitHub)
- `epycloud validate --path ./local/forecast/experiments/test-sim/config` (local)
- `epycloud validate --path ./config --format json` (JSON output)

**Output Example:**
```
Validating: ./local/forecast/experiments/test-sim/config

✓ Validation passed: basemodel_config.yaml + sampling_config.yaml
```

**Exit Codes:**
- 0: Validation passed
- 1: Validation failed (errors found)
- 2: Configuration error (missing token, repo, etc.)

**Commit:** `95401fb` - Implement validate command for config validation

---

### 2025-11-07: Status and Logs Commands
**Implemented:** `epycloud status` and `epycloud logs` for pipeline monitoring

**Status Command:**
- Monitor active workflows and Cloud Batch jobs
- Watch mode with auto-refresh (--watch --interval N)
- Filter by experiment ID (--exp-id)
- Shows execution ID, stage, status, task progress
- Color-coded status output (RUNNING/SUCCEEDED/FAILED)
- Real-time updates in watch mode

**Logs Command:**
- View Cloud Batch job logs via Cloud Logging API
- Required: --exp-id (experiment ID)
- Optional filters: --run-id, --stage (A/B/C), --task-index
- Follow mode for real-time streaming (--follow)
- Tail mode (--tail N, default 100)
- Time-based filtering (--since 1h/30m/24h)
- Severity filtering (--level DEBUG/INFO/WARNING/ERROR)
- Color-coded severity output
- Context display (stage, task index)

**Key Features:**
- Uses Cloud Workflows API and gcloud CLI for Batch logs
- Zero new dependencies (urllib, subprocess only)
- Watch mode with Ctrl+C handling
- Proper timestamp parsing and formatting
- Auto-refresh with configurable interval

**Usage:**
```bash
# Check status once
epycloud status

# Watch status with auto-refresh
epycloud status --watch --interval 10

# View logs for experiment
epycloud logs --exp-id flu-2024

# Stream logs in follow mode
epycloud logs --exp-id flu-2024 --follow

# View specific stage logs
epycloud logs --exp-id flu-2024 --stage B --task-index 5
```

**Commit:** `05f93e3` - Implement status and logs commands for pipeline monitoring

---

## Phase 3 Completion Summary

**Date:** 2025-11-07
**Status:** ✅ COMPLETE

All Phase 3 commands implemented and functional:
- ✅ `validate` - Validates experiment configs from GitHub or local paths
- ✅ `status` - Monitors active workflows and batch jobs with watch mode
- ✅ `logs` - Views and streams Cloud Batch logs with filtering

**Key Achievements:**
- Zero new dependencies initially (updated: added requests library)
- Professional CLI experience with color coding and formatting
- Real-time monitoring with watch/follow modes
- Comprehensive error handling
- Multiple output formats (text/json/yaml for validate)

**Next Phase:** Phase 4 - Polish & Documentation (bash completion, migration guide, v0.1.0 release)

---

## Post-Phase 3 Improvements (2025-11-08 to 2025-11-14)

### Critical Hardening Items Completed ✅

**1. Custom Exception Hierarchy** (2025-11-07)
- File: `src/epycloud/exceptions.py` (114 lines)
- Classes: `EpycloudError`, `ConfigError`, `ValidationError`, `CloudAPIError`, `ResourceNotFoundError`
- **Status:** Production ready and in use

**2. Input Validation Layer** (2025-11-07)
- File: `src/epycloud/lib/validation.py` (307 lines)
- Functions: `validate_exp_id()`, `validate_run_id()`, `validate_local_path()`, `validate_github_token()`, `validate_stage_name()`
- **Status:** Production ready and in use

**3. Integration Tests** (2025-11-07)
- Files: `tests/integration/test_validation.py` (238 lines), `tests/integration/test_run_command.py` (229 lines)
- Coverage: 34 tests passing (< 1 second execution)
- **Status:** Continuously passing

**4. Command Helpers Library** (2025-11-08)
- File: `src/epycloud/lib/command_helpers.py` (268 lines)
- Provides: `CommandContext` TypedDict, `require_config()`, `get_google_cloud_config()`, `handle_dry_run()`, etc.
- **Impact:** Reduced code duplication, improved type safety

**5. Formatters Library** (2025-11-08)
- File: `src/epycloud/lib/formatters.py` (479 lines)
- Provides: Timestamp, duration, status, table formatting functions
- **Impact:** Consistent output across all commands

### Technical Decisions Updated

**6. Library Migration: urllib → requests** (2025-11-10)
- **Decision:** Migrated from stdlib `urllib` to `requests` library
- **Added dependency:** `requests>=2.31.0`
- **Rationale:**
  - `requests` is the de facto standard for HTTP in Python
  - Simpler, more Pythonic API
  - Built-in retry support (Session with adapters)
  - Better error handling
  - Easier to test with mocking
- **Trade-off:** Added one dependency, but worth it for maintainability
- **Status:** ✅ Completed, all HTTP calls migrated

**7. Documentation Update Strategy** (2025-11-12)
- **Decision:** Use `epycloud` directly in all documentation (not `uv run`)
- **Rationale:**
  - Reflects recommended installation method (`uv tool install .`)
  - User/operator mode is primary use case
  - Simpler commands for end users
  - Developer mode (`uv run`) documented separately for contributors
- **Impact:** All docs updated (README, operations.md, google-cloud-guide.md, CLAUDE.md)
- **Status:** ✅ Completed

**8. Code Organization Improvements** (2025-11-13)
- **Decision:** Reorganize Docker scripts and remove deprecated code
- **Changes:**
  - Moved `scripts/` → `docker/scripts/`
  - Removed `jobs/` directory (old Batch job templates)
  - Removed `scripts/run-task-cloud.sh` and `scripts/run-output-cloud.sh`
  - Simplified Makefile to reference epycloud CLI only
- **Impact:** Removed 1,150 lines of outdated code, cleaner project structure
- **Status:** ✅ Completed

### User Experience Improvements

**9. CLI Help Enhancements** (2025-11-10 to 2025-11-11)
- Added subcommand documentation and examples
- Moved examples to epilog for better readability
- Show help by default when no subcommand provided
- Capitalized section titles (Usage:, Options:, etc.)
- Added newline after "Usage:" for readability
- **Status:** ✅ Completed

**10. Configuration Commands Enhanced** (2025-11-12 to 2025-11-13)
- Added `config list-envs` - List available environments dynamically
- Added `config edit-secrets` - Edit secrets file directly
- Fixed `config edit` to open base config by default
- Load environment choices dynamically from config directory
- Improved GitHub PAT error messages
- Fixed GitHub PAT loading from secrets.yaml
- **Status:** ✅ Completed

### Current State (2025-11-14)

**Version:** 0.2.0
**Status:** In Active Production Use

**Codebase Stats:**
- Total Python lines: 7,744
- Commands implemented: 9 (all MVP commands)
- Tests passing: 34 integration tests
- Documentation files: 9 comprehensive docs

**Installation:**
```bash
# Recommended (user/operator mode)
uv tool install .

# Development mode
uv sync
uv run epycloud --version
```

**Team Adoption:**
- Successfully deployed to team
- In active production use
- Feedback loop established
- Continuous improvements based on usage

---

## Remaining Work (Phase 4 and Beyond)

### Phase 4: Polish & Documentation

**Not Started:**
- [ ] Bash/zsh completion scripts (3-4 hours)
- [ ] Migration guide for users (2-3 hours)
- [ ] v0.1.0 release preparation

**In Progress:**
- [ ] Fix pipeline test import error (1-2 hours)
- [ ] Add comprehensive retry logic (2-3 hours)

**Deferred:**
- [ ] Command unit tests (8-10 hours) - integration tests sufficient for now
- [ ] Performance optimizations (2-3 hours) - not needed yet

### Phase 5: Future Enhancements

**Not Planned Yet:**
- [ ] PyPI distribution (internal tool, not needed)
- [ ] CI/CD pipeline (blocked on test fix)
- [ ] Advanced monitoring features
- [ ] Cost estimation features

---

## Action Items Summary (2025-11-14)

### Priority 1: Address Soon
1. **Fix Pipeline Test Import Error** (Medium, 1-2 hours)
   - Separate CLI tests from pipeline tests
   - Unblock CI/CD integration

2. **Add Comprehensive Retry Logic** (Medium, 2-3 hours)
   - Configure requests.Session with HTTPAdapter and Retry
   - Add exponential backoff with jitter
   - Configure retryable status codes

### Priority 2: Next Phase
3. **Write Migration Guide** (High for onboarding, 2-3 hours)
   - Installation instructions
   - Makefile → epycloud comparison table
   - Common workflows walkthrough

4. **Bash/Zsh Completion Scripts** (Low, 3-4 hours)
   - Use argcomplete or generate static files
   - Add completion commands
   - Document installation

5. **CI/CD Pipeline** (Medium, 3-4 hours)
   - GitHub Actions for testing
   - Quality gates and coverage

### Priority 3: Future
6. Command unit tests (as needed)
7. Performance optimizations (if users report issues)
8. PyPI distribution (if tool goes public)

---

**Implementation start:** 2025-11-06
**Production deployment:** 2025-11-08

---

**Document version:** 2.0
**Last updated:** 2025-11-14
