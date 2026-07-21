FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    ACHEON_DB=/data/acheon.db

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

RUN addgroup --system acheon \
    && adduser --system --ingroup acheon --no-create-home acheon \
    && mkdir -p /data \
    && chown acheon:acheon /data

USER acheon
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).read()"]

CMD ["acheon", "serve", "--host", "0.0.0.0"]
