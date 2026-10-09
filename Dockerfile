# ClaimShield Nexus: the API and the investigator app in one image.
#   docker compose up -d                 (see docker-compose.yml; add --profile llm for a local LLM on the GPU)
#   docker build -t claimshield . && docker run -p 8000:8000 --env-file .env claimshield
# The React app is built in the first stage and served by the API from the same origin, so no CORS setup is needed.
# The same image runs the offline pipeline:  docker compose run --rm app python -m backend.pipeline.run_all

FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npx vite build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    STATIC_DIR=/app/web AUTH_DB=/app/data/app.db LOG_FORMAT=json
WORKDIR /app
# Pinned versions: the saved models in backend/models/ were written with them.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
COPY backend backend
COPY data data
COPY knowledge knowledge
COPY --from=web /web/dist web
# Runs as an unprivileged user; data/ (accounts, audit log, LLM text) and knowledge/ are the only writable state.
RUN useradd --system --uid 10001 --home /app csn && chown -R csn /app/data /app/knowledge
USER csn
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health/ready', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
