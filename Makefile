.PHONY: up gpu down logs test integration lint gpu-check nvidia-smi config

# RTX 50 : make train-benchmark DEVICE=cuda BLACKWELL=1 BENCHMARK_WEAK_LABELS=1
BLACKWELL ?= 0
ifeq ($(BLACKWELL),1)
GPU_RUNTIME = -f docker-compose.blackwell.yml
endif

.PHONY: documents-up documents-search documents-watch documents-import documents-status
documents-up:
	docker compose up -d --build --wait backend documents frontend

documents-search:
	docker compose exec -T documents python -m workers.documents.cli search $(ARGS)

documents-watch:
	docker compose exec -T documents python -m workers.documents.cli watch $(ARGS)

documents-import:
	docker compose exec -T documents python -m workers.documents.cli import $(ARGS)

documents-status:
	docker compose exec -T documents python -m workers.documents.cli status $(ARGS)

.PHONY: rag-up rag-prepare rag-index rag-search rag-report rag-status rag-result rag-evaluate
rag-up:
	docker compose up -d --build --wait backend documents

rag-prepare:
	docker compose exec -T documents python -m shared.rag.cli prepare

rag-index:
	docker compose exec -T documents python -m shared.rag.cli index $(ARGS)

rag-search:
	docker compose exec -T documents python -m shared.rag.cli search $(ARGS)

rag-report:
	docker compose exec -T documents python -m shared.rag.cli report $(ARGS)

rag-status:
	docker compose exec -T documents python -m shared.rag.cli status $(ARGS)

rag-result:
	docker compose exec -T documents python -m shared.rag.cli result $(ARGS)

rag-evaluate:
	docker compose exec -T documents python -m shared.rag.cli evaluate $(ARGS)

# Ces commandes soumettent des tâches au worker unique ; ARGS contient des
# options CLI locales et ne doit jamais provenir d'une saisie HTTP.
ARCHITECTURE ?= tf_efficientnetv2_b0
ARGS ?=
.PHONY: pretrained-fetch embeddings-extract embeddings-train embeddings-cluster classification-dataset
classification-dataset:
	docker compose exec vision python -m biosentinelle_vision.classification.cli prepare-dataset $(ARGS)

pretrained-fetch:
	docker compose -f docker-compose.yml -f docker-compose.ml.yml -f docker-compose.pretrained.yml run --rm --no-deps vision python -m biosentinelle_vision.classification.pretrained $(ARCHITECTURE) --root /storage/models/pretrained

embeddings-extract:
	docker compose exec vision python -m biosentinelle_vision.classification.cli extract-embeddings $(ARGS)

embeddings-train:
	docker compose exec vision python -m biosentinelle_vision.classification.cli train-embeddings $(ARGS)

embeddings-cluster:
	docker compose exec vision python -m biosentinelle_vision.classification.cli cluster-embeddings $(ARGS)

.PHONY: classifiers-compare classifier-promote classifier-rollback
classifiers-compare:
	docker compose exec vision python -m biosentinelle_vision.classification.cli compare-classifiers $(ARGS)

classifier-promote:
	docker compose exec vision python -m biosentinelle_vision.classification.cli promote-model $(ARGS)

classifier-rollback:
	docker compose exec vision python -m biosentinelle_vision.classification.cli rollback-model $(ARGS)

up:
	docker compose up -d --build --wait

gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml $(GPU_RUNTIME) up -d --build --wait

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
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml $(GPU_RUNTIME) run --build --rm --no-deps vision python -m workers.vision.cuda_check

nvidia-smi:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml $(GPU_RUNTIME) run --build --rm --no-deps vision nvidia-smi

config:
	docker compose config --quiet
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml $(GPU_RUNTIME) config --quiet

# Les valeurs sont transmises par l'environnement, jamais interpolées dans le shell.
DEVICE ?= cpu
IMAGE ?=
REAL_VIDEO ?= /storage/datasets/inbox/test.mp4
INFER_STRIDE ?= 10
VIDEO ?=
MANIFEST ?= /storage/results/vision/training.json
ALLOW_FILENAME_LABELS ?= 1
DETECTOR ?= /storage/models/md_v5a.0.0.pt
CHECKPOINT ?= /storage/checkpoints/classifier_v3_best.pt
BATCH_SIZE ?= 2
ACCUMULATION_STEPS ?= 4
IMAGE_SIZE ?= 224
TRAIN_CONFIG ?= /app/workers/vision/configs/classifier-rtx3050.json
EPOCHS_HEAD ?= 6
EPOCHS_FINETUNE ?= 18
FORCE ?= 0
POLL_SECONDS ?= 2
STABLE_SECONDS ?= 10
export BIOSENTINELLE_VISION_DEVICE = $(DEVICE)
export BIOSENTINELLE_VISION_DIAGNOSTIC_IMAGE = $(IMAGE)
export BIOSENTINELLE_VISION_INFER_EVERY_N_FRAMES = $(INFER_STRIDE)
export BIOSENTINELLE_REAL_VIDEO = $(REAL_VIDEO)
export BIOSENTINELLE_REAL_OUTPUT = /storage/results/vision/integration
export BIOSENTINELLE_VISION_TRAIN_MANIFEST = $(MANIFEST)
export BIOSENTINELLE_VISION_DETECTOR_WEIGHTS = $(DETECTOR)
export BIOSENTINELLE_VISION_CLASSIFIER_CHECKPOINT = $(CHECKPOINT)
export BIOSENTINELLE_VISION_ANALYSIS_VIDEO = $(VIDEO)
export BIOSENTINELLE_VISION_ANALYSIS_FORCE = $(FORCE)
export BIOSENTINELLE_VISION_WATCH_POLL_SECONDS = $(POLL_SECONDS)
export BIOSENTINELLE_VISION_WATCH_STABLE_SECONDS = $(STABLE_SECONDS)
export BIOSENTINELLE_VISION_TRAINING__BATCH_SIZE = $(BATCH_SIZE)
export BIOSENTINELLE_VISION_TRAINING__ACCUMULATION_STEPS = $(ACCUMULATION_STEPS)
export BIOSENTINELLE_VISION_TRAINING__IMAGE_SIZE = $(IMAGE_SIZE)
export BIOSENTINELLE_VISION_TRAINING__ALLOW_FILENAME_LABELS = $(ALLOW_FILENAME_LABELS)
export BIOSENTINELLE_VISION_TRAINING__EPOCHS_HEAD = $(EPOCHS_HEAD)
export BIOSENTINELLE_VISION_TRAINING__EPOCHS_FINETUNE = $(EPOCHS_FINETUNE)

ML_ENV = --env BIOSENTINELLE_VISION_DEVICE --env BIOSENTINELLE_VISION_TRAIN_MANIFEST \
	--env BIOSENTINELLE_VISION_INFER_EVERY_N_FRAMES \
	--env BIOSENTINELLE_VISION_DETECTOR_WEIGHTS \
	--env BIOSENTINELLE_VISION_CLASSIFIER_CHECKPOINT \
	--env BIOSENTINELLE_VISION_ANALYSIS_VIDEO --env BIOSENTINELLE_VISION_ANALYSIS_FORCE \
	--env BIOSENTINELLE_VISION_TRAINING__BATCH_SIZE \
	--env BIOSENTINELLE_VISION_TRAINING__ACCUMULATION_STEPS \
	--env BIOSENTINELLE_VISION_TRAINING__IMAGE_SIZE \
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
ML_COMPOSE = docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.ml.yml $(GPU_RUNTIME)
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

.PHONY: detector-fetch detector-info detector-test inference-up
detector-fetch: ml-init
	docker compose --profile tools run --build --rm --no-deps detector-download

detector-info: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps vision biosentinelle-vision detector-info

detector-test: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) --env BIOSENTINELLE_VISION_DIAGNOSTIC_IMAGE vision biosentinelle-vision detect-image

inference-up:
	$(ML_COMPOSE) up -d --build --wait

.PHONY: inference-test
inference-test: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) --env BIOSENTINELLE_REAL_VIDEO --env BIOSENTINELLE_REAL_OUTPUT --volume ./tests:/app/tests:ro --volume ./pyproject.toml:/app/pyproject.toml:ro vision python -m pytest /app/tests/vision/test_real_inference.py -m real_model -p no:cacheprovider

export BIOSENTINELLE_TRAIN_CONFIG = $(TRAIN_CONFIG)
ifneq ($(strip $(RESUME)),)
export BIOSENTINELLE_TRAIN_RESUME = $(RESUME)
TRAIN_ENV = --env BIOSENTINELLE_TRAIN_RESUME
endif

.PHONY: training-up train-classifier evaluate-classifier training-tests
training-up: inference-up

# Entraînements complets et séquentiels ; les labels faibles restent une option explicite.
BENCHMARK_WEAK_LABELS ?= 0
CAMPAIGN_ID ?=
export BENCHMARK_WEAK_LABELS CAMPAIGN_ID
export CAMPAIGN_EPOCHS_HEAD = $(EPOCHS_HEAD)
export CAMPAIGN_EPOCHS_FINETUNE = $(EPOCHS_FINETUNE)
export CAMPAIGN_BATCH_SIZE = $(BATCH_SIZE)
export CAMPAIGN_ACCUMULATION_STEPS = $(ACCUMULATION_STEPS)
.PHONY: train-benchmark
train-benchmark: training-up
	$(MAKE) pretrained-fetch ARCHITECTURE=tf_efficientnetv2_b0
	$(MAKE) pretrained-fetch ARCHITECTURE=efficientnetv2_s
	$(MAKE) pretrained-fetch ARCHITECTURE=convnext_tiny
	$(MAKE) pretrained-fetch ARCHITECTURE=resnet50
	$(ML_COMPOSE) exec -T --env BENCHMARK_WEAK_LABELS --env CAMPAIGN_ID --env CAMPAIGN_EPOCHS_HEAD --env CAMPAIGN_EPOCHS_FINETUNE --env CAMPAIGN_BATCH_SIZE --env CAMPAIGN_ACCUMULATION_STEPS vision python -m biosentinelle_vision.training.campaign --device $(DEVICE)

.PHONY: efficientnet-poc-check train-efficientnet-poc
efficientnet-poc-check:
	$(ML_COMPOSE) exec -T vision python -m biosentinelle_vision.training.poc --config /app/workers/vision/configs/classifier-efficientnetv2-poc.json

train-efficientnet-poc:
	$(ML_COMPOSE) exec -T vision python -m biosentinelle_vision.training.poc --config /app/workers/vision/configs/classifier-efficientnetv2-poc.json --submit

train-classifier: MANIFEST = /storage/results/vision/review.json
train-classifier: ml-init
	docker compose run --build --rm --no-deps $(ML_ENV) $(TRAIN_ENV) --env BIOSENTINELLE_TRAIN_CONFIG vision biosentinelle-vision train-classifier

evaluate-classifier: MANIFEST = /storage/results/vision/review.json
evaluate-classifier: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps $(ML_ENV) vision biosentinelle-vision evaluate-classifier

training-tests: ml-init
	$(ML_COMPOSE) run --build --rm --no-deps --volume ./tests:/app/tests:ro --volume ./pyproject.toml:/app/pyproject.toml:ro vision python -m pytest /app/tests/vision/test_training_resume.py /app/tests/vision/test_ml_optional.py -m ml -p no:cacheprovider

.PHONY: training-gpu-test
training-gpu-test: training-up
	$(ML_COMPOSE) run --rm --no-deps --env BIOSENTINELLE_TRAINING_QUEUE_TEST=1 --volume ./tests:/app/tests:ro --volume ./pyproject.toml:/app/pyproject.toml:ro vision python -m pytest /app/tests/vision/test_training_gpu_queue.py -m gpu -p no:cacheprovider

.PHONY: review-up review-tests
review-up: inference-up

review-tests:
	docker compose --profile test run --build --rm tests pytest tests/test_review.py tests/test_review_integration.py -m "not gpu"

.PHONY: web-test web-e2e web-training-test
NPM ?= npm
web-test:
	cd frontend && $(NPM) run test

web-e2e:
	cd frontend && $(NPM) run test:e2e

web-training-test:
	docker compose -f docker-compose.yml -f docker-compose.web-tests.yml --profile test run --build --rm tests
