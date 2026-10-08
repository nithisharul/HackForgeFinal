# API image (build context: project root). Not used on the free plan; kept for Cloudflare Containers
# (Workers Paid) or any Docker host:  docker build -f cloudflare/Dockerfile -t claimshield-api . && docker run -p 8000:8000 claimshield-api
FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Only what the API imports at runtime, at the versions pinned in backend/requirements.txt.
# scikit-learn, igraph and leidenalg are needed to rebuild the pipeline, not to serve it.
COPY backend/requirements.txt /tmp/requirements.txt
RUN grep -E '^(fastapi|uvicorn|pandas|numpy)==' /tmp/requirements.txt > /tmp/runtime.txt \
 && pip install --no-cache-dir -r /tmp/runtime.txt

COPY backend backend
COPY data data
COPY knowledge knowledge

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
