#!/bin/bash
set -euo pipefail

# Shell wrapper for main_output.py
# Handles cloning private GitHub forecast repo before running output generator (cloud mode only)

# Environment detection
EXECUTION_MODE="${EXECUTION_MODE:-cloud}"

echo "=== Starting Stage C: Output Generation (mode: ${EXECUTION_MODE}) ==="

# Load shared GitHub utility functions
source "$(dirname "$0")/github_utils.sh"

# Validate required environment variables
check_required_vars() {
    local missing_vars=()

    if [ -z "${EXP_ID:-}" ]; then
        missing_vars+=("EXP_ID")
    fi

    if [ -z "${NUM_TASKS:-}" ]; then
        missing_vars+=("NUM_TASKS")
    fi

    if [ "$EXECUTION_MODE" = "cloud" ]; then
        if [ -z "${GCS_BUCKET:-}" ]; then
            missing_vars+=("GCS_BUCKET")
        fi
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "ERROR: Required environment variables not set:"
        printf '  - %s\n' "${missing_vars[@]}"
        echo ""
        echo "Required variables:"
        echo "  EXP_ID          Experiment identifier"
        echo "  NUM_TASKS       Number of Stage B result files to load"
        if [ "$EXECUTION_MODE" = "cloud" ]; then
            echo "  GCS_BUCKET      GCS bucket name (cloud mode)"
        fi
        echo ""
        echo "Optional variables:"
        echo "  RUN_ID          Run identifier (default: 'unknown')"
        echo "  DIR_PREFIX      Directory prefix (default: 'pipeline/flu/')"
        echo "  LOCAL_DATA_PATH Local data path (default: '/data')"
        exit 1
    fi
}

# Display configuration
display_config() {
    echo "Configuration:"
    echo "  Execution mode: ${EXECUTION_MODE}"
    echo "  Experiment ID:  ${EXP_ID}"
    echo "  Run ID:         ${RUN_ID:-unknown}"
    echo "  Dir prefix:     ${DIR_PREFIX:-pipeline/flu/}"
    echo "  Number of tasks: ${NUM_TASKS}"

    if [ "$EXECUTION_MODE" = "cloud" ]; then
        echo "  GCS bucket:     ${GCS_BUCKET}"
    else
        echo "  Local data path: ${LOCAL_DATA_PATH:-/data}"
    fi
    echo ""
}

# Function to cleanup repo tarball from GCS (no longer needed after Stage B)
cleanup_repo_tarball() {
    if [ -z "${GCS_BUCKET:-}" ] || [ -z "${DIR_PREFIX:-}" ] || [ -z "${EXP_ID:-}" ] || [ -z "${RUN_ID:-}" ]; then
        return 0
    fi

    local gcs_path="gs://${GCS_BUCKET}/${DIR_PREFIX}${EXP_ID}/${RUN_ID}/repo-cache/forecast-repo.tar.gz"

    if gsutil -q stat "$gcs_path" 2>/dev/null; then
        echo "Cleaning up forecast repo tarball from GCS..."
        gsutil -q rm "$gcs_path"
        echo "✓ Repo tarball removed from GCS"
    fi
}

# Main execution
main() {
    # Validate environment
    check_required_vars
    display_config

    if [ "$EXECUTION_MODE" = "cloud" ]; then
        # Cleanup tarball from GCS (no longer needed after Stage B)
        cleanup_repo_tarball

        echo "Cloud mode: Setting up forecast repository..."

        # Only clone forecast repo if GITHUB_FORECAST_REPO is set
        if [ -n "${GITHUB_FORECAST_REPO:-}" ]; then
            setup_github_auth
            clone_forecast_repo
        else
            echo "GITHUB_FORECAST_REPO not set, skipping forecast repo clone"
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

    # Run the main output generator
    echo "Running main_output.py..."
    python3 -u "$(dirname "$0")/main_output.py" "$@"

    echo "=== Stage C complete ==="
}

# Run main function
main "$@"
