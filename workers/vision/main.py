import os

from shared.worker_runtime import run


def main() -> None:
    if os.getenv("REQUIRE_CUDA", "0") == "1":
        from workers.vision.cuda_check import check_cuda

        check_cuda()
    if os.getenv("VISION_CONSUME_JOBS", "0") == "1":
        from biosentinelle_vision.job_worker import run as consume

        consume()
    else:
        run("vision")


if __name__ == "__main__":
    main()
