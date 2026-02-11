# Installation

Learn how to install the `epycloud` CLI tool for managing serverless epidemic modeling pipelines on Google Cloud.

## Prerequisites

- **Operating System**: Linux or macOS (Windows via WSL)
- **Python**: 3.11 or higher (managed by uv)
- **Git**: For cloning the repository
- **Google Cloud Account**: For cloud deployments (optional for local development)

## Install with uv

This method installs `epycloud` as a globally available command without affecting your system Python.

### Step 1: Install uv Package Manager

[uv](https://docs.astral.sh/uv/) is a fast Python package and project manager, written in Rust. We use it to install `epycloud` as an isolated CLI tool.

<!-- link-card: https://docs.astral.sh/uv/ -->

Install:
```console
$ curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your shell or run:
```console
$ source ~/.bashrc  # or ~/.zshrc for zsh users
```

### Step 2: Install epycloud

```console
$ git clone https://github.com/mobs-lab/epymodelingsuite-cloud
$ cd epymodelingsuite-cloud

$ uv tool install .

$ epycloud --version
```

The tool will be installed in `~/.local/bin/epycloud`.


### Step 3: Update epycloud

When pulling new code changes:

```console
$ cd epymodelingsuite-cloud
$ git pull
$ uv tool upgrade epycloud
```

## Alternative: Development Mode

For contributing to epycloud or developing features:

```console
$ git clone https://github.com/mobs-lab/epymodelingsuite-cloud
$ cd epymodelingsuite-cloud

$ uv sync

$ uv run epycloud --help
$ uv run epycloud config show
```

!!! tip "When to Use Development Mode"
    - Contributing to the epycloud project
    - Testing local code changes before committing
    - Debugging CLI functionality

    For regular usage, stick with the regular installation.

## Verify Installation

After installation, verify `epycloud` is available:

```console
$ epycloud --version

$ epycloud --help

$ epycloud config --help
```

Expected output:
```txt
epycloud 0.3.12
```

## Next Steps

1. **[Quick Start](local.md)**: Initialize configuration and run your first workflow
2. **[Configuration Guide](../user-guide/configuration.md)**: Learn about the configuration system

## Troubleshooting

### Command not found: epycloud

If `epycloud` is not found after installation:

1. Check that `~/.local/bin` is in your `PATH`:
```console
$ echo $PATH | grep -q "$HOME/.local/bin" && echo "Found" || echo "Not found"
```

2. Add to PATH if missing (add to `~/.bashrc` or `~/.zshrc`):
```console
$ export PATH="$HOME/.local/bin:$PATH"
```

3. Restart your shell or source the config:
```console
$ source ~/.bashrc  # or ~/.zshrc
```
