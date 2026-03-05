#!/bin/bash
set -euo pipefail

# Shell wrapper for main_builder.py
# Handles cloning private GitHub forecast repo before running the builder (cloud mode only)

# Environment detection
EXECUTION_MODE="${EXECUTION_MODE:-cloud}"

# Configuration
FORECAST_REPO_DIR="${FORECAST_REPO_DIR:-/data/forecast/}"

echo "=== Starting builder wrapper (mode: ${EXECUTION_MODE}) ==="

# Load shared GitHub utility functions
source "$(dirname "$0")/github_utils.sh"

# Function to upload repo tarball to GCS for Stage B (cloud mode only)
# This avoids N parallel git clones from Stage B tasks
upload_repo_tarball() {
    if [ -z "${GCS_BUCKET:-}" ] || [ -z "${DIR_PREFIX:-}" ] || [ -z "${EXP_ID:-}" ] || [ -z "${RUN_ID:-}" ]; then
        echo "Warning: Missing GCS config, skipping tarball upload"
        return 0
    fi

    echo "Creating repo tarball for Stage B..."
    local tarball_path="/tmp/forecast-repo.tar.gz"
    local gcs_path="gs://${GCS_BUCKET}/${DIR_PREFIX}${EXP_ID}/${RUN_ID}/repo-cache/forecast-repo.tar.gz"

    # Create tarball from the cloned repo
    tar -czf "$tarball_path" -C "$(dirname "$FORECAST_REPO_DIR")" "$(basename "$FORECAST_REPO_DIR")"

    # Upload to GCS
    echo "Uploading tarball to: $gcs_path"
    gsutil -q cp "$tarball_path" "$gcs_path"

    # Cleanup local tarball
    rm -f "$tarball_path"

    echo "✓ Repo tarball uploaded to GCS for Stage B"
}

# Main execution
main() {
    if [ "$EXECUTION_MODE" = "cloud" ]; then
        echo "Cloud mode: Setting up forecast repository..."

        # Only clone forecast repo if GITHUB_FORECAST_REPO is set
        if [ -n "${GITHUB_FORECAST_REPO:-}" ]; then
            setup_github_auth
            clone_forecast_repo
            # Upload tarball to GCS for Stage B to download (avoids N parallel git clones)
            upload_repo_tarball
        else
            echo "GITHUB_FORECAST_REPO not set, skipping forecast repo clone"
        fi
    else
        echo "Local mode: Skipping forecast repository clone"
        echo "Using local forecast data from mounted volume (if present)"

        # Add local forecast directory to PYTHONPATH if it exists
        # The forecast directory can be at /data/forecast
        if [ -d "/data/forecast" ]; then
            export PYTHONPATH="/data/forecast:${PYTHONPATH:-}"
            echo "✓ Added to PYTHONPATH: /data/forecast"
        else
            echo "Note: /data/forecast not found (optional)"
        fi
    fi

    # Run the main builder with all arguments
    echo "Running main_builder.py..."
    python3 -u "$(dirname "$0")/main_builder.py" "$@"

    echo "=== Builder complete ==="
}

# Run main function
main "$@"
