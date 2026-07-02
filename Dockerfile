# Use a lightweight python 3.14 base image
FROM python:3.14-slim-bookworm

# Install uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Prevent uv from sending telemetry
ENV UV_NO_ANALYTICS=1

# Copy configuration and lockfiles for dependency caching
COPY pyproject.toml uv.lock README.md ./

# Install dependencies without installing the project itself
RUN uv sync --frozen --no-dev --no-install-project

# Copy the actual source code
COPY src/ src/

# Sync again to install the package itself
RUN uv sync --frozen --no-dev

# Ensure virtualenv bin path is in the execution PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run the MCP server via stdio transport by default
CMD ["lightrag-mcp"]
