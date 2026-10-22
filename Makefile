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

# Les valeurs sont transmises par l'environnement, jamais interpolées dans le shell.
DEVICE ?= cpu
VIDEO ?=
MANIFEST ?= /storage/results/vision/training.json
ALLOW_FILENAME_LABELS ?= 1
DETECTOR ?= /storage/models/md_v5a.0.0.pt
CHECKPOINT ?= /storage/checkpoints/classifier_v3_best.pt
BATCH_SIZE ?= 4
EPOCHS_HEAD ?= 6
EPOCHS_FINETUNE ?= 18
FORCE ?= 0
POLL_SECONDS ?= 2
STABLE_SECONDS ?= 10
export BIOSENTINELLE_VISION_DEVICE = $(DEVICE)
export BIOSENTINELLE_VISION_TRAIN_MANIFEST = $(MANIFEST)
export BIOSENTINELLE_VISION_DETECTOR_WEIGHTS = $(DETECTOR)
export BIOSENTINELLE_VISION_CLASSIFIER_CHECKPOINT = $(CHECKPOINT)
export BIOSENTINELLE_VISION_ANALYSIS_VIDEO = $(VIDEO)
export BIOSENTINELLE_VISION_ANALYSIS_FORCE = $(FORCE)
export BIOSENTINELLE_VISION_WATCH_POLL_SECONDS = $(POLL_SECONDS)
export BIOSENTINELLE_VISION_WATCH_STABLE_SECONDS = $(STABLE_SECONDS)
export BIOSENTINELLE_VISION_TRAINING__BATCH_SIZE = $(BATCH_SIZE)
export BIOSENTINELLE_VISION_TRAINING__ALLOW_FILENAME_LABELS = $(ALLOW_FILENAME_LABELS)
export BIOSENTINELLE_VISION_TRAINING__EPOCHS_HEAD = $(EPOCHS_HEAD)
export BIOSENTINELLE_VISION_TRAINING__EPOCHS_FINETUNE = $(EPOCHS_FINETUNE)

ML_ENV = --env BIOSENTINELLE_VISION_DEVICE --env BIOSENTINELLE_VISION_TRAIN_MANIFEST \
	--env BIOSENTINELLE_VISION_DETECTOR_WEIGHTS \
	--env BIOSENTINELLE_VISION_CLASSIFIER_CHECKPOINT \
	--env BIOSENTINELLE_VISION_ANALYSIS_VIDEO --env BIOSENTINELLE_VISION_ANALYSIS_FORCE \
	--env BIOSENTINELLE_VISION_TRAINING__BATCH_SIZE \
	--env BIOSENTINELLE_VISION_TRAINING__ALLOW_FILENAME_LABELS \
	--env BIOSENTINELLE_VISION_TRAINING__EPOCHS_HEAD \
	--env BIOSENTINELLE_VISION_TRAINING__EPOCHS_FINETUNE \
	--env BIOSENTINELLE_VISION_WATCH_POLL_SECONDS \
	--env BIOSENTINELLE_VISION_WATCH_STABLE_SECONDS

ifneq ($(strip $(INITIAL_CHECKPOINT)),)
export BIOSENTINELLE_VISION_INITIAL_CHECKPOINT = $(INITIAL_CHECKPOINT)
ML_ENV += --env BIOSENTINELLE_VISION_INITIAL_CHECKPOINT
endif

ifeq ($(DEVICE),cpu)
ML_COMPOSE = docker compose -f docker-compose.yml -f docker-compose.ml.yml
else ifeq ($(DEVICE),cuda)
ML_COMPOSE = docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.ml.yml
else
$(error DEVICE doit valoir cpu ou cuda)
endif

.PHONY: ml-init ml-build train-check train analyze watch classify-videos prepare-training
prepare-training: classify-videos
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) vision biosentinelle-vision prepare-training --inventory /storage/results/vision/classification/videos.json

classify-videos: ml-init
	docker compose -f docker-compose.yml -f docker-compose.data.yml run --build --rm --no-deps vision biosentinelle-vision organize /source --destination /storage/datasets/classified --reports /storage/results/vision/classification

ml-init:
	docker compose run --rm --no-deps storage-init

ml-build: ml-init
	$(ML_COMPOSE) build vision

train-check: ml-init
	docker compose run --build --rm --no-deps $(ML_ENV) vision biosentinelle-vision train --check-only

train: train-check
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) vision biosentinelle-vision train

analyze: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) vision biosentinelle-vision analyze

watch: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) vision biosentinelle-vision watch
