# Ritmo backend — FastAPI + SQLAlchemy (Postgres, AD-007)
# Config 100% por env vars: DATABASE_URL vem do compose, nunca daqui.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

WORKDIR /app

# Dependências primeiro (cache de camadas entre builds)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Código da app (tests/.venv ficam fora via .dockerignore)
COPY app ./app

# Zonas VDOT calibradas - fonte de verdade do endpoint de detalhe
COPY data ./data

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
