# =============================================================================
# Project Relay — Multi-stage Production Dockerfile
# Python 3.12 with uv fast package manager
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project dependencies configuration
COPY pyproject.toml uv.lock* ./

# Install dependencies into virtual environment
RUN uv venv /app/.venv && \
    uv sync --frozen --no-dev --no-install-project

# =============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user for security
RUN groupadd -r relay && useradd -r -g relay -s /bin/false relay

# Copy virtualenv and dependencies from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy application source code
COPY src/ /app/src/
COPY apps/ /app/apps/
COPY migrations/ /app/migrations/
COPY alembic.ini /app/alembic.ini
COPY pyproject.toml /app/pyproject.toml

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Ensure files are owned by non-root user
RUN chown -R relay:relay /app
USER relay

EXPOSE 8000 8001

CMD ["uv", "run", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
