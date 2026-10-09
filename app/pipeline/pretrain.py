import os
import pandas as pd

from .forecasting import train_forecaster
from .preprocessing import prepare_data


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


DATA_FILE = os.path.join(
    BASE_DIR,
    "demand_forecasting.csv"
)


def build_series(
    data,
    product,
    store
):

    filtered = data[
        data["product"].astype(str)
        == str(product)
    ]

    filtered = filtered[
        filtered["store"].astype(str)
        == str(store)
    ]

    if filtered.empty:
        return None

    history = (
        filtered
        .groupby(
            [
                "date",
                "product",
                "store"
            ],
            as_index=False
        )
        .agg({
            "quantity": "sum",
            "price": "mean",
            "discount": "mean"
        })
        .sort_values(
            "date"
        )
        .reset_index(
            drop=True
        )
    )

    return history


def pretrain_all():

    if not os.path.exists(
        DATA_FILE
    ):
        print(
            f"[PRETRAIN] Dataset not found: {DATA_FILE}"
        )
        return

    print(
        "\n========================================"
    )
    print(
        " DemandPulse AI - Model Pretraining"
    )
    print(
        "========================================"
    )

    print(
        "[PRETRAIN] Loading dataset..."
    )

    raw = pd.read_csv(
        DATA_FILE
    )

    data = prepare_data(
        raw
    )

    products = (
        data["product"]
        .dropna()
        .astype(str)
        .unique()
    )

    stores = (
        data["store"]
        .dropna()
        .astype(str)
        .unique()
    )

    total = (
        len(products)
        * len(stores)
    )

    completed = 0

    print(
        f"[PRETRAIN] Products: {len(products)}"
    )

    print(
        f"[PRETRAIN] Stores: {len(stores)}"
    )

    print(
        f"[PRETRAIN] Series: {total}"
    )

    print(
        "[PRETRAIN] Training models..."
    )

    for product in products:

        for store in stores:

            history = build_series(
                data,
                product,
                store
            )

            completed += 1

            if (
                history is None
                or len(history) < 5
            ):
                print(
                    f"[PRETRAIN] "
                    f"{completed}/{total} "
                    f"{product}-{store} skipped"
                )
                continue

            try:

                train_forecaster(
                    history
                )

                print(
                    f"[PRETRAIN] "
                    f"{completed}/{total} "
                    f"{product}-{store} READY"
                )

            except Exception as e:

                print(
                    f"[PRETRAIN] "
                    f"{completed}/{total} "
                    f"{product}-{store} FAILED: {e}"
                )

    print(
        "\n[PRETRAIN] Complete."
    )

    print(
        "[PRETRAIN] Forecast requests are now cache-backed."
    )

    print(
        "========================================\n"
    )


if __name__ == "__main__":
    pretrain_all()