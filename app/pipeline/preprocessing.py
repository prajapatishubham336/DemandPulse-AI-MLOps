import numpy as np
import pandas as pd


def prepare_data(data):
    data = data.copy()

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data["quantity"] = pd.to_numeric(data["quantity"], errors="coerce")
    data = data.dropna(subset=["date", "quantity"])

    if "price" in data.columns:
        data["price"] = pd.to_numeric(data["price"], errors="coerce").fillna(1.0)
    else:
        data["price"] = 1.0

    if "discount" in data.columns:
        data["discount"] = pd.to_numeric(data["discount"], errors="coerce").fillna(0.0)
    else:
        data["discount"] = 0.0

    data["quantity"] = data["quantity"].clip(lower=0)
    data = (data.groupby(["date", "product", "store"], as_index=False)
        .agg({
            "quantity": "sum",
            "price": "mean",
            "discount": "mean"
        })
        .sort_values("date")
    )
    return data


def fill_missing_dates(data):
    data = data.copy()

    if data.empty:
        return data

    data = data.sort_values("date")
    dates = pd.date_range(data["date"].min(),data["date"].max(), freq="D")
    data = (data.set_index("date").reindex(dates).rename_axis("date").reset_index())
    data["quantity"] = data["quantity"].fillna(0)
    data["product"] = (data["product"].ffill().bfill().fillna("Unknown"))
    data["store"] = (data["store"].ffill().bfill().fillna("ALL"))
    data["price"] = (data["price"].ffill().bfill().fillna(1.0))
    data["discount"] = (data["discount"].fillna(0))
    return data


def clean_numeric_columns(data):
    data = data.copy()

    for column in ["quantity", "price", "discount"]:
        if column in data.columns:
            data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.replace([np.inf, -np.inf], np.nan)
    return data


def prepare_for_forecasting(data):
    data = clean_numeric_columns(data)
    data = prepare_data(data)
    return data