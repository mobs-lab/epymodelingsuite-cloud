# epycloud: Design and Architecture

**Version:** 1.0
**Created:** 2025-11-06
**Status:** Approved

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Installation Design](#installation-design)
4. [Configuration System](#configuration-system)
5. [CLI Design](#cli-design)
6. [Implementation Plan](#implementation-plan)
7. [Migration Strategy](#migration-strategy)

---

## Executive Summary

### Vision

Transform `epymodelingsuite-cloud` from a Makefile-based workflow into a professional, installable CLI tool (`epycloud`) with:

- **Modern package structure** - Installable via pip
- **Clean configuration** - YAML-based with environment/profile support
- **Intuitive CLI** - Professional command interface
- **XDG-compliant** - Standard config directories
- **Backward compatible** - Existing workflows continue to work

### Key Changes

| Aspect | Before | After |
|--------|--------|-------|
| CLI | `make build` | `epycloud build` |
| Config | `.env` files | `config.yaml` + profiles |
| Installation | Clone repo | `pip install epycloud` |
| Config location | `./.env` | `~/.config/epymodelingsuite-cloud/` |
| Environments | Manual | Automatic (dev/prod/local) |
| Projects | N/A | Profiles (flu/covid/rsv) |

### Goals

1. **Environment Separation** - Clear dev/prod/local isolation
2. **Better Configuration** - Structured YAML instead of `.env`
3. **Modern CLI** - Professional tool, use from anywhere
4. **Minimal Dependencies** - Only stdlib + existing PyYAML
5. **Backward Compatibility** - Keep existing workflows working

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
├─────────────────────────────────────────────────────────────┤
│  epycloud [--env ENV] [--profile PROFILE] COMMAND [ARGS]    │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                     src/epycloud/cli.py                      │
│              (argparse command routing)                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                  src/epycloud/config/                        │
│         (Load config.yaml + merge env/profile)               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                src/epycloud/commands/*.py                    │
│   (build.py, run.py, workflow.py, terraform.py, etc.)       │
└─────────────────────────────────────────────────────────────┘
```

### Component Overview

**CLI Layer** (`cli.py`):
- Argument parsing with argparse
- Command routing
- Global options (--env, --profile, --verbose)
- Help text generation

**Config Layer** (`config/`):
- YAML config loading
- Environment/profile merging
- Secret management
- Environment variable overrides

**Command Layer** (`commands/`):
- Individual command implementations
- Reusable logic
- Error handling

**Utility Layer** (`utils/`):
- Storage abstraction (GCS/local)
- Logging
- Output formatting

---

## Installation Design

### Package Structure

**Package name:** `epycloud`
**Repository name:** `epymodelingsuite-cloud` (unchanged)

```
epymodelingsuite-cloud/
├── pyproject.toml              # Modern Python packaging
├── README.md
├── LICENSE
├── src/
│   └── epycloud/               # Installable package
│       ├── __init__.py         # Version info
│       ├── __main__.py         # python -m epycloud
│       ├── cli.py              # Main CLI entry point
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py       # Config loading/merging
│       │   └── templates/      # Config templates
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── build.py        # Build commands
│       │   ├── run.py          # Run commands
│       │   ├── workflow.py     # Workflow management
│       │   ├── terraform.py    # Infrastructure
│       │   ├── config_cmd.py   # Config management
│       │   ├── profile.py      # Profile management
│       │   ├── verify.py       # Experiment verification
│       │   ├── status.py       # Status monitoring
│       │   └── logs.py         # Log viewing
│       ├── lib/
│       │   ├── __init__.py
│       │   ├── output.py       # Pretty output (ANSI colors)
│       │   ├── validation.py   # Validation helpers
│       │   └── paths.py        # XDG path management
│       └── utils/
│           ├── __init__.py
│           ├── storage.py      # GCS/local storage abstraction
│           └── logger.py       # Logging utilities
├── scripts/                    # Pipeline scripts (Docker execution)
│   ├── main_builder.py         # Stage A
│   ├── main_runner.py          # Stage B
│   ├── main_output.py          # Stage C
│   └── run_builder.sh          # Builder wrapper
├── docker/
│   ├── Dockerfile
│   └── requirements.txt
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── workflow.yaml
├── tests/
│   ├── test_config.py
│   ├── test_cli.py
│   └── test_commands.py
└── docs/
    ├── design-and-architecture.md  # This document
    ├── configuration-guide.md
    ├── command-reference.md
    └── implementation-decisions.md
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "epycloud"
version = "0.1.0"
description = "CLI for epymodelingsuite cloud pipeline management"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    {name = "MOBS Lab", email = "contact@mobs-lab.org"}
]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3.11",
]

dependencies = [
    "google-cloud-storage>=2.18.2",
    "numpy>=1.24.0",
    "pandas>=2.0.0",
    "scipy>=1.11.0",
    "epydemix>=1.0.1",
    "dill>=0.4.0",
    "python-json-logger>=2.0.7",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
]

[project.scripts]
epycloud = "epycloud.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

### Installation Methods

**Recommended: Install as isolated CLI tool with uv:**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install epycloud as isolated CLI tool
cd epymodelingsuite-cloud
uv tool install .

# Use directly (no environment activation needed)
epycloud --version
```

**Development installation with uv:**
```bash
cd epymodelingsuite-cloud

# Create virtual environment and install dependencies
uv sync

# Run in development mode
epycloud --version

# Or activate the virtual environment
source .venv/bin/activate
epycloud --version
```

**Alternative: Run without installing:**
```bash
uv tool run --from /path/to/epymodelingsuite-cloud epycloud --version
```

**Legacy: pip installation (not recommended):**
```bash
# Editable install (development)
pip install -e .

# User install
pip install --user .
```

**From Git (future):**
```bash
uv tool install git+https://github.com/mobs-lab/epymodelingsuite-cloud.git
```

**From PyPI (future):**
```bash
uv tool install epycloud
```

---

## Configuration System

### XDG Directory Structure

```
~/.config/epymodelingsuite-cloud/     # XDG_CONFIG_HOME
├── config.yaml                        # Base configuration
├── secrets.yaml                       # Secrets (gitignored)
├── active_profile                     # Current profile: "flu"
├── environments/                      # Infrastructure environments
│   ├── dev.yaml                      # Development overrides
│   ├── prod.yaml                     # Production overrides
│   └── local.yaml                    # Local development
└── profiles/                          # Project/disease profiles
    ├── flu.yaml                       # Flu forecasting
    ├── covid.yaml                     # COVID modeling
    └── rsv.yaml                       # RSV modeling

~/.local/share/epymodelingsuite-cloud/ # XDG_DATA_HOME
└── cache/

~/.cache/epymodelingsuite-cloud/       # XDG_CACHE_HOME
└── build-cache/
```

### Configuration Hierarchy

**Merge order (lowest to highest priority):**

1. **Base config** - `~/.config/epymodelingsuite-cloud/config.yaml`
2. **Environment config** - `environments/{env}.yaml` (dev/prod/local)
3. **Profile config** - `profiles/{profile}.yaml` (flu/covid/rsv)
4. **Project config** - `./epycloud.yaml` (optional, in current directory)
5. **Environment variables** - `EPYCLOUD_*`
6. **Command-line arguments** - `--project-id`, etc.

### Environment vs Profile

**Environment (dev/prod/local)** - Infrastructure target:
- CLI argument: `epycloud --env=prod`
- **Explicit** - always visible
- **Stateless** - no hidden state
- Controls: Resources, GCP project, deployment target

**Profile (flu/covid/rsv)** - Project configuration:
- Activation: `epycloud profile use flu`
- **Stateful** - persists between commands (like conda)
- **Convenient** - don't repeat on every command
- Controls: Forecast repo, default settings, project-specific resources

---

## CLI Design

### Command Structure

```
epycloud [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]

Global Options:
  -h, --help              Show help
  -v, --version           Show version
  -e, --env ENV           Environment: dev|prod|local (default: dev)
  --profile PROFILE       Override active profile
  -c, --config PATH       Config file path
  -d, --project-dir PATH  Project directory
  --verbose               Verbose output
  --quiet                 Quiet mode
  --dry-run               Show what would happen
```

### Main Commands (MVP)

**Essential (Phases 1-3):**
- `config` - Configuration management
- `profile` - Profile management (disease/project)
- `build` - Docker image building
- `run` - Execute pipeline stages/workflows
- `workflow` - Workflow management
- `terraform` (alias: `tf`) - Infrastructure management
- `validate` - Validate experiment configuration
- `status` - Pipeline status monitoring
- `logs` - View pipeline logs

**Low Priority (Phase 2):**
- `download` - Download results from GCS
- `list` - List experiments/runs/outputs

**Deferred:**
- `cost` - Cost estimation (complex, use GCP console)
- `init` - Project initialization (manual `epycloud.yaml` is fine)

### Entry Point

```python
# src/epycloud/cli.py

import sys
import argparse
from pathlib import Path

from epycloud.config.loader import ConfigLoader
from epycloud.lib.output import info, error
from epycloud.lib.paths import ensure_config_dir
from epycloud import commands


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog='epycloud',
        description='Epidemic modeling pipeline management CLI',
    )

    # Global options
    parser.add_argument('--env', '-e', choices=['dev', 'prod', 'local'], default='dev')
    parser.add_argument('--profile', help='Override active profile')
    parser.add_argument('--config', '-c', type=Path, help='Config file path')
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--quiet', '-q', action='store_true')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command')

    # Register command parsers
    commands.config_cmd.register_parser(subparsers)
    commands.profile.register_parser(subparsers)
    commands.build.register_parser(subparsers)
    commands.run.register_parser(subparsers)
    commands.workflow.register_parser(subparsers)
    commands.terraform.register_parser(subparsers)
    commands.verify.register_parser(subparsers)
    commands.status.register_parser(subparsers)
    commands.logs.register_parser(subparsers)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load configuration
    ensure_config_dir()
    config_loader = ConfigLoader(
        environment=args.env,
        profile=args.profile,
        config_path=args.config,
    )
    config = config_loader.load()

    # Create context
    ctx = {
        'config': config,
        'environment': args.env,
        'profile': config.active_profile,
        'verbose': args.verbose,
        'quiet': args.quiet,
        'args': args,
    }

    # Route to command handler
    try:
        if args.command == 'config':
            commands.config_cmd.handle(ctx)
        elif args.command == 'profile':
            commands.profile.handle(ctx)
        # ... etc
    except KeyboardInterrupt:
        print()
        sys.exit(130)
    except Exception as e:
        error(f"Command failed: {e}")
        if ctx['verbose']:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
```

---

## Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)

**Objective:** Create package structure and config system

**Tasks:**
1. Create `src/epycloud/` package structure
2. Create `pyproject.toml` with package metadata
3. Implement config loader (`config/loader.py`)
4. Implement XDG path management (`lib/paths.py`)
5. Create config templates
6. Implement `epycloud config init` command
7. Unit tests for config loading

**Deliverables:**
- Installable package: `pip install -e .`
- Working command: `epycloud --version`
- Config initialization: `epycloud config init`
- Tests passing

### Phase 2: Core Commands (Week 2)

**Objective:** Implement essential commands

**Tasks:**
1. Implement `build` commands (cloud/local/dev)
2. Implement `run` commands (workflow/job)
3. Implement `workflow` commands (run/list/describe)
4. Implement `terraform` commands (init/plan/apply/destroy)
5. Implement `profile` commands (use/list/create/show)
6. Integration tests

**Deliverables:**
- Working build/run/workflow/terraform commands
- Profile management working
- Backward compatibility verified

### Phase 3: Advanced Features (Week 3) ✅ COMPLETED

**Objective:** Add monitoring and verification

**Tasks:**
1. ✅ Implement `validate` command (GitHub API integration + local validation)
2. ✅ Implement `status` command (workflow + batch job monitoring)
3. ✅ Implement `logs` command (Cloud Logging integration)
4. ✅ Error handling improvements
5. ✅ Output formatting polish

**Deliverables:**
- ✅ Experiment validation working (remote and local)
- ✅ Status monitoring working (with watch mode)
- ✅ Log viewing working (with follow mode)

**Status:** Phase 3 completed on 2025-11-07. All monitoring and validation commands are functional.

### Phase 4: Polish & Documentation (Week 4)

**Objective:** Production-ready release

**Tasks:**
1. Add bash/zsh completion scripts
2. Write comprehensive documentation
3. Create migration guide
4. End-to-end testing
5. Performance optimization

**Deliverables:**
- Complete documentation
- Migration guide for users
- Completion scripts
- v0.1.0 release ready

### Future: PyPI Distribution

**Tasks:**
- Semantic versioning setup
- Changelog automation
- CI/CD for releases
- PyPI publishing

---

## Migration Strategy

### Backward Compatibility Approach

**Dual Mode Support:**
- Both `.env` and `config.yaml` work during transition
- Existing Makefile commands continue to work
- New CLI commands available alongside
- No forced breaking changes

### Migration Path for Users

**Step 1: Install New System (No impact)**
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install epycloud as isolated tool
cd epymodelingsuite-cloud
uv tool install .

# Existing workflow still works
make build
```

**Step 2: Initialize Config**
```bash
# Create config directory and files
epycloud config init

# Interactive setup
epycloud config setup
```

**Step 3: Test New CLI**
```bash
# Try new commands
epycloud --env=dev config show
epycloud --env=dev build cloud

# Compare with old workflow
make build  # Still works
```

**Step 4: Create Profiles**
```bash
# Create disease-specific profiles
epycloud profile create flu
epycloud profile create covid

# Edit profiles
epycloud profile edit flu
```

**Step 5: Use New Workflow**
```bash
# Activate profile
epycloud profile use flu

# Run from anywhere (not just repo directory)
cd ~/experiments/
epycloud --env=dev verify --exp-id test
epycloud --env=dev run workflow --exp-id test
```

### Data Migration

**GCS Storage Paths:**
- Old: `gs://bucket/pipeline/flu/exp-id/run-id/`
- New: `gs://bucket/pipeline/dev/flu/exp-id/run-id/`

**Migration:**
- No automatic migration
- Old and new paths coexist
- Optional: Migrate data with `gsutil -m mv`

**Recommendation:** Leave old data in place, new runs use new structure.

### Rollback Plan

If issues occur:
1. Keep `Makefile` as backup
2. Continue using `.env` files
3. Report issues for fixing
4. Uninstall package: `pip uninstall epycloud`

---

## Benefits

### 1. Professional Tool

**Before:**
```bash
cd /path/to/epymodelingsuite-cloud
source .env
make build
```

**After:**
```bash
# Use from anywhere
cd ~/my-experiments/
epycloud build
```

### 2. Environment Safety

**Before:**
- Manual `DIR_PREFIX` changes
- Easy to accidentally run in wrong environment
- No safeguards

**After:**
- Explicit `--env` flag required
- Confirmation prompts for production
- Environment-specific resources
- Clear visual indicators

### 3. Configuration Management

**Before:**
- Scattered across `.env`, `Makefile`, `terraform.tfvars`
- No single source of truth
- Manual synchronization

**After:**
- Single `config.yaml` source of truth
- Environment/profile overrides
- Clear inheritance model
- Secrets separate in `secrets.yaml`

### 4. Better Developer Experience

**Improved CLI:**
- Proper help: `epycloud --help`
- Subcommands: `epycloud workflow list`
- Type validation
- Colored output
- Better error messages

**Example:**
```
Before: ERROR: EXP_ID is required but not set.

After:  ✗ Experiment ID is required. Use --exp-id=<id>
        Example: epycloud run workflow --exp-id=test-sim
```

### 5. Maintainability

**Code organization:**
- Modular command structure
- Testable Python code
- Type hints and docstrings
- Clean separation of concerns
- Makefile: 378 lines → 50 lines (87% reduction)

---

## Success Criteria

### Phase 1 Complete
- [ ] Package installable with `pip install -e .`
- [ ] Config directory initialized
- [ ] Config loading and merging works
- [ ] Unit tests passing

### Phase 2 Complete
- [ ] All core commands functional
- [ ] Profile management working
- [ ] Backward compatibility verified
- [ ] Integration tests passing

### Phase 3 Complete
- [x] Validate/status/logs commands working
- [x] Error handling robust
- [x] Output formatting polished

### Phase 4 Complete
- [ ] Documentation complete
- [ ] Migration guide published
- [ ] Completion scripts available
- [ ] v0.1.0 released

### Final Success
- [ ] Dev/prod separation working safely
- [ ] Configuration management simplified
- [ ] CLI UX significantly improved
- [ ] No breaking changes for existing users
- [ ] Team adopting new workflow

---

## Code Quality Standards

### Docstring Style

**Standard:** NumPy-style docstrings

All Python code must use NumPy-style docstrings for consistency and readability.

**Example:**
```python
def load_config(environment, profile, config_path=None):
    """
    Load and merge configuration from multiple sources.

    Parameters
    ----------
    environment : str
        Environment name (dev, prod, local).
    profile : str or None
        Profile name (flu, covid, rsv). If None, uses active profile.
    config_path : str or Path, optional
        Custom config file path. Default is None (use XDG config dir).

    Returns
    -------
    dict
        Merged configuration dictionary.

    Raises
    ------
    ConfigError
        If configuration is invalid or required files are missing.

    Examples
    --------
    >>> config = load_config('dev', 'flu')
    >>> config['google_cloud']['project_id']
    'modeling-dev'
    """
    pass
```

**Reference:** [NumPy Documentation Guide](https://numpydoc.readthedocs.io/en/latest/format.html)

### Code Formatting and Linting

**Tool:** `ruff`

All Python files must be formatted and linted with `ruff` before committing.

**When to run:**
- After editing any Python file
- Before committing changes
- As part of pre-commit hooks (future)

**Commands:**
```bash
# Format and fix auto-fixable issues
ruff check --fix src/epycloud/

# Check specific file
ruff check src/epycloud/cli.py

# Format all Python files
ruff format src/epycloud/

# Run both check and format
ruff check --fix src/epycloud/ && ruff format src/epycloud/
```

**Configuration:**
- `ruff` configuration is in `pyproject.toml`
- Line length: 100 characters
- Target Python version: 3.11
- Import sorting: enabled
- Automatic fixes: enabled when safe

---

## Dependencies

**Current (unchanged):**
```
google-cloud-storage==2.18.2
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.11.0
epydemix>=1.0.1
dill>=0.4.0
python-json-logger>=2.0.7
pyyaml>=6.0  # Already used
```

**New dependencies:** None (0)

**Development dependencies:**
```
pytest>=7.0
pytest-cov>=4.0
ruff>=0.1.0
```

---

## Timeline Estimate

**Total development time:** 3-4 weeks

- **Week 1:** Package structure, config system (Phase 1)
- **Week 2:** Core commands (Phase 2)
- **Week 3:** Advanced features (Phase 3)
- **Week 4:** Polish and documentation (Phase 4)

---

**Document version:** 1.0
**Last updated:** 2025-11-06
