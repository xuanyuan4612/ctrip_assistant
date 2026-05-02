# =============================================================================
# Dockerfile: ctrip/app
# Multi-stage build for the FastAPI + LangGraph backend.
#
# Build stage: Installs Python dependencies via Poetry.
# Run stage:   Minimal image with app code and dependencies.
# =============================================================================

# ---- Build Stage ----
FROM python:3.11-slim AS builder

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.3 \
    POETRY_HOME=/opt/poetry \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Copy dependency manifest
WORKDIR /build
COPY pyproject.toml poetry.lock* ./

# Install production dependencies only (no dev)
RUN poetry install --only main --no-root --no-interaction

# ---- Run Stage ----
FROM python:3.11-slim AS runner

# Create non-root user
RUN groupadd -r ctrip && useradd -r -g ctrip -d /app -s /sbin/nologin ctrip

# Install runtime system dependencies (e.g., mysql client for migrations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder
COPY --from=builder /build/.venv /build/.venv
ENV PATH="/build/.venv/bin:$PATH"

# Create app directory and set ownership
WORKDIR /app
COPY --chown=ctrip:ctrip app/ ./app/
COPY --chown=ctrip:ctrip migrations/ ./migrations/
COPY --chown=ctrip:ctrip data/ ./data/
COPY --chown=ctrip:ctrip alembic.ini ./alembic.ini 2>/dev/null || true

# Switch to non-root user
USER ctrip

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

# Start the FastAPI application with Uvicorn
# Note: --factory tells uvicorn that the application is a factory function
CMD ["uvicorn", "app.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory", "--workers", "4"]
