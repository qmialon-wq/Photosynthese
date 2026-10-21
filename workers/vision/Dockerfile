FROM python:3.12.12-slim-bookworm AS cpu
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app
COPY workers/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --uid 10001 --create-home biosentinelle
COPY shared /app/shared
COPY workers /app/workers
USER biosentinelle
CMD ["python", "-m", "workers.vision.main"]
