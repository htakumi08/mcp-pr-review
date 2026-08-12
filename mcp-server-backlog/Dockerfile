FROM python:3.13.15-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

COPY pyproject.toml README.md ./
COPY src ./src

FROM base AS development

RUN python -m pip install --no-cache-dir --editable '.[dev]'

COPY tests ./tests

USER app

CMD ["python", "-m", "backlog_mcp"]

FROM base AS runtime

RUN python -m pip install --no-cache-dir .

USER app

ENTRYPOINT ["python", "-m", "backlog_mcp"]

