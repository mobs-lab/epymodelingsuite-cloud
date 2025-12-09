#!/bin/bash
set -euo pipefail

# Shell wrapper for main_output.py
# Handles cloning private GitHub forecast repo before running output generator (cloud mode only)

# Environment detection
EXECUTION_MODE="${EXECUTION_MODE:-cloud}"

# Configuration
FORECAST_REPO="${GITHUB_FORECAST_REPO:-}"
FORECAST_REPO_DIR="${FORECAST_REPO_DIR:-/data/forecast/}"
SECRET_NAME="${GITHUB_PAT_SECRET:-github-pat}"
PROJECT_ID="${GCLOUD_PROJECT_ID:-}"

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

# Function to setup GitHub authentication (cloud mode only)
setup_github_auth() {
    echo "Setting up GitHub authentication from Secret Manager..."

    if [ -z "$PROJECT_ID" ]; then
        echo "ERROR: GCLOUD_PROJECT_ID must be set for cloud mode"
        exit 1
    fi

    if [ -z "$SECRET_NAME" ]; then
        echo "ERROR: GITHUB_PAT_SECRET must be set for cloud mode"
        exit 1
    fi

    echo "Fetching GitHub PAT from Secret Manager: $SECRET_NAME"

    # Get access token from metadata server
    ACCESS_TOKEN=$(curl -s -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" | \
        python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

    # Fetch secret using REST API
    GITHUB_PAT=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        "https://secretmanager.googleapis.com/v1/projects/${PROJECT_ID}/secrets/${SECRET_NAME}/versions/latest:access" | \
        python3 -c "import sys, json, base64; print(base64.b64decode(json.load(sys.stdin)['payload']['data']).decode('utf-8'))")

    export GITHUB_PAT
    echo "✓ GitHub PAT configured from Secret Manager"
}

# Function to clone the forecast repository (cloud mode only)
clone_forecast_repo() {
    if [ -z "$FORECAST_REPO" ]; then
        echo "ERROR: GITHUB_FORECAST_REPO environment variable not set"
        exit 1
    fi

    if [ -z "$GITHUB_PAT" ]; then
        echo "ERROR: GITHUB_PAT not retrieved from Secret Manager"
        exit 1
    fi

    # Remove existing directory if present
    if [ -d "$FORECAST_REPO_DIR" ]; then
        echo "Removing existing directory..."
        rm -rf "$FORECAST_REPO_DIR"
    fi

    echo "Cloning forecast repository: $FORECAST_REPO"

    # Clone the repository using HTTPS with PAT
    # Format: https://oauth2:TOKEN@github.com/owner/repo.git
    REPO_URL="https://oauth2:${GITHUB_PAT}@github.com/${FORECAST_REPO}.git"
    git clone --quiet "$REPO_URL" "$FORECAST_REPO_DIR"

    echo "✓ Repository cloned to: $FORECAST_REPO_DIR"

    # Optionally checkout specific branch/tag
    if [ -n "${FORECAST_REPO_REF:-}" ]; then
        echo "Checking out ref: $FORECAST_REPO_REF"
        cd "$FORECAST_REPO_DIR"
        git checkout "$FORECAST_REPO_REF"
        cd -
    fi

    # Add to PYTHONPATH
    export PYTHONPATH="${FORECAST_REPO_DIR}:${PYTHONPATH:-}"
    echo "✓ Added to PYTHONPATH: $FORECAST_REPO_DIR"
}

# Main execution
main() {
    # Validate environment
    check_required_vars
    display_config

    if [ "$EXECUTION_MODE" = "cloud" ]; then
        echo "Cloud mode: Setting up forecast repository..."

        # Only clone forecast repo if FORECAST_REPO is set
        if [ -n "$FORECAST_REPO" ]; then
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
