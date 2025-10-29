#!/bin/bash
set -euo pipefail

# Shell wrapper for main_output.py
# Generates output files from Stage B results

# Environment detection
EXECUTION_MODE="${EXECUTION_MODE:-cloud}"

echo "=== Starting Stage C: Output Generation (mode: ${EXECUTION_MODE}) ==="

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

# Main execution
main() {
    # Validate environment
    check_required_vars
    display_config

    # Run the main output generator
    echo "Running main_output.py..."
    python3 -u "$(dirname "$0")/main_output.py" "$@"

    echo "=== Stage C complete ==="
}

# Run main function
main "$@"
