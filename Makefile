.PHONY: up gpu down logs test integration lint gpu-check nvidia-smi config

up:
	docker compose up -d --build --wait

gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build --wait

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

test:
	docker compose --profile test run --build --rm tests

integration:
	docker compose --profile test run --build --rm tests pytest -m integration

lint:
	docker compose --profile test run --build --rm tests ruff check backend shared workers tests infra/init_storage.py

gpu-check:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --build --rm --no-deps vision python -m workers.vision.cuda_check

nvidia-smi:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --build --rm --no-deps vision nvidia-smi

config:
	docker compose config --quiet
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet
