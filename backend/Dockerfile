FROM python:3.12.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/app/backend
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && useradd --uid 10001 --create-home biosentinelle
COPY backend /app/backend
COPY shared /app/shared
USER biosentinelle
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test
ENV PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest-cache" RUFF_CACHE_DIR=/tmp/ruff-cache
USER root
COPY infra/requirements-test.txt /tmp/requirements-test.txt
RUN pip install --no-cache-dir -r /tmp/requirements-test.txt
COPY pyproject.toml /app/pyproject.toml
COPY tests /app/tests
COPY workers /app/workers
COPY infra/init_storage.py /app/infra/init_storage.py
USER biosentinelle
CMD ["pytest", "-m", "not integration and not gpu"]
