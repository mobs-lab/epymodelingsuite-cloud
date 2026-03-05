#!/bin/bash
# Shared GitHub utility functions for pipeline scripts
# Source this file: source "$(dirname "$0")/github_utils.sh"

# Setup GitHub authentication via Secret Manager (cloud mode only)
# Requires: GCLOUD_PROJECT_ID, GITHUB_PAT_SECRET
# Exports: GITHUB_PAT
setup_github_auth() {
    local project_id="${GCLOUD_PROJECT_ID:-}"
    local secret_name="${GITHUB_PAT_SECRET:-github-pat}"

    echo "Setting up GitHub authentication from Secret Manager..."

    if [ -z "$project_id" ]; then
        echo "ERROR: GCLOUD_PROJECT_ID must be set for cloud mode"
        exit 1
    fi

    if [ -z "$secret_name" ]; then
        echo "ERROR: GITHUB_PAT_SECRET must be set for cloud mode"
        exit 1
    fi

    echo "Fetching GitHub PAT from Secret Manager: $secret_name"

    # Get access token from metadata server
    local access_token
    access_token=$(curl -s -H "Metadata-Flavor: Google" \
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" | \
        python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

    # Fetch secret using REST API
    GITHUB_PAT=$(curl -s -H "Authorization: Bearer ${access_token}" \
        "https://secretmanager.googleapis.com/v1/projects/${project_id}/secrets/${secret_name}/versions/latest:access" | \
        python3 -c "import sys, json, base64; print(base64.b64decode(json.load(sys.stdin)['payload']['data']).decode('utf-8'))")

    export GITHUB_PAT
    echo "✓ GitHub PAT configured from Secret Manager"
}

# Clone a git repo with retry and exponential backoff
# Args: $1 = repo URL, $2 = destination directory
git_clone_with_retry() {
    local url="$1"
    local dest="$2"
    local max_retries=3
    local delay=10

    for attempt in $(seq 1 $max_retries); do
        if git clone --quiet --depth 1 "$url" "$dest"; then
            return 0
        fi

        if [ "$attempt" -lt "$max_retries" ]; then
            echo "Clone attempt $attempt/$max_retries failed, retrying in ${delay}s..."
            rm -rf "$dest"
            sleep "$delay"
            delay=$((delay * 2))
        fi
    done

    echo "ERROR: git clone failed after $max_retries attempts"
    return 1
}

# Clone the forecast repository using HTTPS with PAT
# Requires: GITHUB_FORECAST_REPO, GITHUB_PAT
# Optional: FORECAST_REPO_DIR (default: /data/forecast/), FORECAST_REPO_REF
clone_forecast_repo() {
    local forecast_repo="${GITHUB_FORECAST_REPO:-}"
    local forecast_repo_dir="${FORECAST_REPO_DIR:-/data/forecast/}"

    if [ -z "$forecast_repo" ]; then
        echo "ERROR: GITHUB_FORECAST_REPO environment variable not set"
        exit 1
    fi

    if [ -z "${GITHUB_PAT:-}" ]; then
        echo "ERROR: GITHUB_PAT not retrieved from Secret Manager"
        exit 1
    fi

    # Remove existing directory if present
    if [ -d "$forecast_repo_dir" ]; then
        echo "Removing existing directory..."
        rm -rf "$forecast_repo_dir"
    fi

    echo "Cloning forecast repository: $forecast_repo"

    # Clone the repository using HTTPS with PAT
    local repo_url="https://oauth2:${GITHUB_PAT}@github.com/${forecast_repo}.git"
    git_clone_with_retry "$repo_url" "$forecast_repo_dir"

    echo "✓ Repository cloned to: $forecast_repo_dir"

    # Optionally checkout specific branch/tag
    if [ -n "${FORECAST_REPO_REF:-}" ]; then
        echo "Checking out ref: $FORECAST_REPO_REF"
        cd "$forecast_repo_dir"
        git checkout "$FORECAST_REPO_REF"
        cd -
    fi

    # Add to PYTHONPATH
    export PYTHONPATH="${forecast_repo_dir}:${PYTHONPATH:-}"
    echo "✓ Added to PYTHONPATH: $forecast_repo_dir"
}
