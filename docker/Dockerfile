FROM python:3.11-slim

# Install system dependencies (git and gcloud CLI for Secret Manager)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && curl -sSL https://sdk.cloud.google.com | bash \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for gcloud (it expects /usr/bin/python3)
RUN ln -s /usr/local/bin/python3 /usr/bin/python3

# Add gcloud to PATH
ENV PATH="/root/google-cloud-sdk/bin:${PATH}"

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY docker/requirements.txt .

# Install dependencies with uv (much faster than pip)
RUN uv pip install --system --no-cache -r requirements.txt

# Copy application scripts
COPY scripts/ /scripts/
RUN chmod +x /scripts/*.sh

# Default entrypoint - Workflows will override via commands
ENTRYPOINT ["/bin/bash", "/scripts/run_dispatcher.sh"]
