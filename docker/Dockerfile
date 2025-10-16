# =============================================================================
# Base Stage - Common dependencies for both local and cloud
# =============================================================================
FROM python:3.11-slim AS base

# Install git (needed for cloning modeling suite)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY docker/requirements.txt .

# Install dependencies with uv (much faster than pip)
RUN uv pip install --system --no-cache -r requirements.txt

# Clone and install flumodelingsuite package
# Expects GITHUB_MODELING_SUITE_REPO, GITHUB_MODELING_SUITE_REF, and GITHUB_PAT to be passed as build args
ARG GITHUB_MODELING_SUITE_REPO
ARG GITHUB_MODELING_SUITE_REF=main
ARG GITHUB_PAT

# Clone the flumodelingsuite repository and install it in editable mode
# Using editable install (-e) to work around missing validation subpackage issue
RUN if [ -n "$GITHUB_MODELING_SUITE_REPO" ] && [ -n "$GITHUB_PAT" ]; then \
    git clone --branch ${GITHUB_MODELING_SUITE_REF} \
        https://${GITHUB_PAT}@github.com/${GITHUB_MODELING_SUITE_REPO}.git /opt/flumodelingsuite && \
    uv pip install --system -e /opt/flumodelingsuite; \
    fi

# Copy application scripts
COPY scripts/ /scripts/
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
FROM base AS cloud

# Install curl and gcloud CLI for Secret Manager access
RUN apt-get update && apt-get install -y \
    curl \
    && curl -sSL https://sdk.cloud.google.com | bash \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for gcloud (it expects /usr/bin/python3)
RUN ln -s /usr/local/bin/python3 /usr/bin/python3

# Add gcloud to PATH
ENV PATH="/root/google-cloud-sdk/bin:${PATH}"

# Default entrypoint - Workflows will override via commands
ENTRYPOINT ["/bin/bash", "/scripts/run_dispatcher.sh"]
