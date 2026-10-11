# Web app: builds the React UI, then serves it and the API with uvicorn.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY agrof_vision/ agrof_vision/
COPY --from=web /web/dist web/dist
RUN uv sync --frozen --no-dev
ENV HOST=0.0.0.0 PORT=8000 PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
USER nobody
CMD ["python", "-m", "agrof_vision"]
