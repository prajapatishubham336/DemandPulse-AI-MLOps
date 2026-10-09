import os
import sys


def main():

    print(
        "\n========================================"
    )

    print(
        " DemandPulse AI"
    )

    print(
        "========================================"
    )

    print(
        "[1/2] Checking model cache..."
    )

    cache_dir = os.path.join(
        "app",
        "pipeline",
        "model_cache"
    )

    os.makedirs(
        cache_dir,
        exist_ok=True
    )

    cache_files = [
        f
        for f in os.listdir(
            cache_dir
        )
        if f.endswith(".pkl")
    ]

    if not cache_files:

        print(
            "[CACHE] No trained models found."
        )

        print(
            "[CACHE] Running one-time pretraining..."
        )

        from app.pipeline.pretrain import (
            pretrain_all
        )

        pretrain_all()

    else:

        print(
            f"[CACHE] Found {len(cache_files)} trained model(s)."
        )

        print(
            "[CACHE] Skipping training."
        )

    print(
        "[2/2] Starting FastAPI..."
    )

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )


if __name__ == "__main__":
    main()