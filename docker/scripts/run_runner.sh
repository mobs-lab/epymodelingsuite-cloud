#!/bin/bash
set -euo pipefail

# Shell wrapper for main_runner.py
# Handles cloning private GitHub forecast repo before running the runner (cloud mode only)

# Environment detection
EXECUTION_MODE="${EXECUTION_MODE:-cloud}"

# Configuration
FORECAST_REPO_DIR="${FORECAST_REPO_DIR:-/data/forecast/}"

echo "=== Starting Stage B: Runner (mode: ${EXECUTION_MODE}) ==="

# Load shared GitHub utility functions
source "$(dirname "$0")/github_utils.sh"

# Function to download repo tarball from GCS (uploaded by Stage A)
# This avoids N parallel git clones through NAT
download_repo_tarball() {
    if [ -z "${GCS_BUCKET:-}" ] || [ -z "${DIR_PREFIX:-}" ] || [ -z "${EXP_ID:-}" ] || [ -z "${RUN_ID:-}" ]; then
        echo "Missing GCS config for tarball download"
        return 1
    fi

    local tarball_path="/tmp/forecast-repo.tar.gz"
    local gcs_path="gs://${GCS_BUCKET}/${DIR_PREFIX}${EXP_ID}/${RUN_ID}/repo-cache/forecast-repo.tar.gz"

    echo "Downloading forecast repo tarball from GCS..."
    echo "  Source: $gcs_path"

    # Download from GCS (uses Private Google Access, no NAT needed)
    if ! gsutil -q cp "$gcs_path" "$tarball_path" 2>/dev/null; then
        echo "Tarball not found in GCS"
        return 1
    fi

    # Remove existing directory if present
    if [ -d "$FORECAST_REPO_DIR" ]; then
        rm -rf "$FORECAST_REPO_DIR"
    fi

    # Extract tarball
    mkdir -p "$FORECAST_REPO_DIR"
    tar -xzf "$tarball_path" -C "$FORECAST_REPO_DIR" --strip-components=1

    # Cleanup local tarball
    rm -f "$tarball_path"

    echo "✓ Repo extracted from tarball to: $FORECAST_REPO_DIR"

    # Add to PYTHONPATH
    export PYTHONPATH="${FORECAST_REPO_DIR}:${PYTHONPATH:-}"
    echo "✓ Added to PYTHONPATH: $FORECAST_REPO_DIR"

    return 0
}

# Main execution
main() {
    if [ "$EXECUTION_MODE" = "cloud" ]; then
        echo "Cloud mode: Setting up forecast repository..."

        # Only setup forecast repo if GITHUB_FORECAST_REPO is set
        if [ -n "${GITHUB_FORECAST_REPO:-}" ]; then
            # Try GCS tarball first (uploaded in Stage A), fall back to git clone
            if download_repo_tarball; then
                echo "Using cached repo from GCS tarball"
            else
                echo "Repo tarball not available, falling back to git clone..."
                setup_github_auth
                clone_forecast_repo
            fi
        else
            echo "GITHUB_FORECAST_REPO not set, skipping forecast repo setup"
        fi
    else
        echo "Local mode: Skipping forecast repository clone"
        echo "Using local forecast data from mounted volume (if present)"

        # Add local forecast directory to PYTHONPATH if it exists
        if [ -d "/data/forecast" ]; then
            export PYTHONPATH="/data/forecast:${PYTHONPATH:-}"
            echo "✓ Added to PYTHONPATH: /data/forecast"
        else
            echo "Note: /data/forecast not found (optional)"
        fi
    fi

    # Run the main runner with all arguments
    echo "Running main_runner.py..."
    python3 -u "$(dirname "$0")/main_runner.py" "$@"

    echo "=== Stage B complete ==="
}

# Run main function
main "$@"
