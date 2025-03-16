# mcr.microsoft.com/devcontainers/python:3.13-bookworm
FROM mcr.microsoft.com/devcontainers/base:bookworm

USER vscode

# TODO: this will not be updated by dependabot like this.
RUN curl -LsSf https://astral.sh/uv/0.6.6/install.sh | sh

# Produces unusable links when run from here. Too early for some reason!
# RUN uv sync || true
