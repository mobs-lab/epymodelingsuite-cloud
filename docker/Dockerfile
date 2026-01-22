# =============================================================================
# Base Stage - Common dependencies for both local and cloud
# =============================================================================
FROM python:3.11-slim AS base

# Install git (needed for cloning modeling suite) and curl (needed for gcloud)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Clone and install epymodelingsuite package
# Expects GITHUB_MODELING_SUITE_REPO, GITHUB_MODELING_SUITE_REF, and GITHUB_PAT to be passed as build args
ARG GITHUB_MODELING_SUITE_REPO
ARG GITHUB_MODELING_SUITE_REF=main
ARG GITHUB_PAT

# Install epymodelingsuite from GitHub source, using uv.lock
# This creates a virtual environment at /opt/epymodelingsuite/.venv
RUN if [ -n "$GITHUB_MODELING_SUITE_REPO" ] && [ -n "$GITHUB_PAT" ]; then \
    git clone --branch ${GITHUB_MODELING_SUITE_REF} \
        https://${GITHUB_PAT}@github.com/${GITHUB_MODELING_SUITE_REPO}.git /opt/epymodelingsuite && \
    cd /opt/epymodelingsuite && \
    if [ -f uv.lock ]; then \
        uv sync --frozen; \
    else \
        # Fall back to non-frozen sync if uv.lock does not exist
        echo "WARNING: uv.lock not found; running uv sync without --frozen"; \
        uv sync; \
    fi; \
    fi

# Use the uv-managed venv for runtime Python
ENV VIRTUAL_ENV="/opt/epymodelingsuite/.venv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Install locked cloud-specific dependencies into the same venv as epymodelingsuite
# uv pip install respects VIRTUAL_ENV; export from lock and pipe to install
COPY docker/pyproject.toml docker/uv.lock /app/
RUN uv export --frozen --no-dev | uv pip install --no-cache -r -

# Copy application scripts
COPY docker/scripts/ /scripts/
RUN chmod +x /scripts/*.sh 2>/dev/null || true

# =============================================================================
# Local Stage - Minimal image for local development
# =============================================================================
FROM base AS local

# Default entrypoint for local execution
ENTRYPOINT ["/bin/bash", "/scripts/run_dispatcher.sh"]

# =============================================================================
# Cloud Stage - Full image with gcloud CLI for Secret Manager access
# =============================================================================
# Use official gcloud SDK image to get pre-installed gcloud CLI
FROM gcr.io/google.com/cloudsdktool/cloud-sdk:slim AS gcloud

FROM base AS cloud

# Copy gcloud SDK from the official image
COPY --from=gcloud /usr/lib/google-cloud-sdk /usr/lib/google-cloud-sdk

# Add gcloud to PATH
ENV PATH="/usr/lib/google-cloud-sdk/bin:${PATH}"

# Create symlink for gcloud (it expects /usr/bin/python3)
RUN ln -s /usr/local/bin/python3 /usr/bin/python3 || true

# Default entrypoint - Workflows will override via commands
ENTRYPOINT ["/bin/bash", "/scripts/run_dispatcher.sh"]
