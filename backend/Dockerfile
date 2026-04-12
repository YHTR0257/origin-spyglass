FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install runtime dependencies first for better layer reuse.
COPY pyproject.toml ./
RUN uv sync --no-dev

# Copy application sources.
COPY src ./src

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
