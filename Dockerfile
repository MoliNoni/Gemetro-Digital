# Gemetro Digital API (FastAPI) — used locally via docker-compose and by Render.
#
# The package resolves its data directory from the source layout
# (src/gemetro/paths.py: REPO_ROOT = parents[2] of that file), so the image keeps the
# repository layout under /app — src/ and artifacts/ side by side — and runs from source
# via PYTHONPATH instead of installing the package into site-packages.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only what the API reads at runtime: the package and the versioned artifacts
# (comfort model, ML domain, hourly climate, occupancy shape).
COPY src/ src/
COPY artifacts/ artifacts/

RUN useradd --create-home --uid 10001 gemetro
USER gemetro

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/health', timeout=4)"

# Render injects PORT; locally it defaults to 8000.
CMD ["sh", "-c", "uvicorn gemetro.api:app --host 0.0.0.0 --port ${PORT}"]
