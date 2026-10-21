import os

from shared.worker_runtime import run


def main() -> None:
    if os.getenv("REQUIRE_CUDA", "0") == "1":
        from workers.vision.cuda_check import check_cuda

        check_cuda()
    run("vision")


if __name__ == "__main__":
    main()
