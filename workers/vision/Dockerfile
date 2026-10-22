FROM python:3.12.12-slim-bookworm AS dependencies
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY workers/vision/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --uid 10001 --create-home biosentinelle
FROM dependencies AS cpu
COPY shared /app/shared
COPY workers /app/workers
RUN pip install --no-cache-dir --no-deps /app/workers/vision
USER biosentinelle
CMD ["python", "-m", "workers.vision.main"]

# Image facultative, uniquement construite par les commandes ML explicites.
FROM dependencies AS ml
USER root
COPY workers/vision/requirements-ml-cpu.txt /tmp/requirements-ml-cpu.txt
RUN pip install --no-cache-dir -r /tmp/requirements-ml-cpu.txt
COPY workers/vision/requirements-training.txt /tmp/requirements-training.txt
RUN pip install --no-cache-dir -r /tmp/requirements-training.txt
COPY shared /app/shared
COPY workers /app/workers
RUN pip install --no-cache-dir --no-deps /app/workers/vision
USER biosentinelle
CMD ["python", "-m", "workers.vision.main"]
