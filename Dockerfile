FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && useradd --create-home --shell /usr/sbin/nologin autohealer \
    && mkdir -p /data \
    && chown -R autohealer:autohealer /app /data

ENV PATH="/root/.local/bin:/app/.venv/bin:${PATH}"

COPY --chown=autohealer:autohealer pyproject.toml uv.lock README.md ./
COPY --chown=autohealer:autohealer src ./src

RUN uv sync --frozen --no-dev

USER autohealer

EXPOSE 8080

VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import json, urllib.request; json.load(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3))['status'] == 'ok'" || exit 1

CMD ["auto-healer", "--host", "0.0.0.0", "--port", "8080", "--db", "/data/auto_healer.sqlite3"]
