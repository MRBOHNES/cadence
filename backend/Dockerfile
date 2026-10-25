FROM python:3.14-slim

# uv installs the locked dependencies quickly and reproducibly.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

# On every start: apply migrations, upsert the seed monitors, then serve. Both steps are idempotent.
# Render injects $PORT.
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
