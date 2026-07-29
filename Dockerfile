FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    PATH="/app/.venv/bin:${PATH}" \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

# FAISS needs the OpenMP runtime provided by libgomp1.
RUN apt-get update \
    && apt-get install --no-install-recommends --yes ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app \
    && mkdir -p "${HF_HOME}" \
    && chown -R app:app /home/app

# Install dependencies separately so source-only changes reuse this layer.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY --chown=app:app simple_RAG.py ./

USER app

CMD ["python", "simple_RAG.py"]
