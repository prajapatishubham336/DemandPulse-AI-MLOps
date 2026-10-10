from pathlib import Path

import numpy as np
import pandas as pd

DATE_ALIASES = ["date", "datetime", "timestamp", "day", "week", "period", "ds", "time"]
DEMAND_ALIASES = ["sales", "demand", "quantity", "qty", "units", "units_sold", "volume", "revenue", "target", "y"]
PRODUCT_ALIASES = ["product", "product_id", "sku", "item", "item_id", "article", "category"]
STORE_ALIASES = ["store", "store_id", "location", "branch", "region", "shop"]
PRICE_ALIASES = ["price", "unit_price", "selling_price", "sales_price"]
DISCOUNT_ALIASES = ["discount", "discount_pct", "discount_percent"]


def normalize_name(name):
    return str(name).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def normalize_columns(df):
    # Rename columns in-place; avoid copying a large DataFrame just to normalize headers.
    df.columns = [normalize_name(c) for c in df.columns]
    return df


def find_column(columns, aliases):
    columns = list(columns)
    # Exact matches first, preserving alias priority.
    for alias in aliases:
        if alias in columns:
            return alias
    # Fuzzy matches, preserving original behavior.
    for column in columns:
        for alias in aliases:
            if alias in column or column in alias:
                return column
    return None


def read_file(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        # Low-memory chunked parsing is not used here because column detection and
        # aggregation currently expect a single DataFrame.
        return pd.read_csv(path)
    if suffix == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(path)
    raise ValueError("Invalid file format. Upload CSV or Excel file.")


def adapt_dataset(path):
    df = normalize_columns(read_file(path))

    if df.empty:
        raise ValueError("Invalid dataset: the uploaded file is empty.")

    date_col = find_column(df.columns, DATE_ALIASES)
    demand_col = find_column(df.columns, DEMAND_ALIASES)
    product_col = find_column(df.columns, PRODUCT_ALIASES)
    store_col = find_column(df.columns, STORE_ALIASES)
    price_col = find_column(df.columns, PRICE_ALIASES)
    discount_col = find_column(df.columns, DISCOUNT_ALIASES)

    if date_col is None or demand_col is None:
        raise ValueError(
            "Invalid dataset: a valid date/time column and demand/sales/quantity column are required."
        )

    # Build only the columns needed downstream instead of copying the full source table.
    date_values = pd.to_datetime(df[date_col], errors="coerce")
    quantity_values = pd.to_numeric(df[demand_col], errors="coerce")

    result = pd.DataFrame({
        "date": date_values,
        "quantity": quantity_values,
        "product": df[product_col].astype(str) if product_col else "TOTAL",
        "store": df[store_col].astype(str) if store_col else "ALL",
        "price": pd.to_numeric(df[price_col], errors="coerce") if price_col else 1.0,
        "discount": pd.to_numeric(df[discount_col], errors="coerce") if discount_col else 0.0,
    })

    # Replace non-finite values only in numeric columns (rather than scanning the
    # entire mixed-type DataFrame).
    for col in ("quantity", "price", "discount"):
        result[col] = result[col].replace([np.inf, -np.inf], np.nan)

    result = result.dropna(subset=["date", "quantity"])
    result = result.loc[result["quantity"] >= 0]

    if len(result) < 3:
        raise ValueError("Invalid dataset: not enough valid time-series demand records.")

    result["product"] = result["product"].replace({"nan": "TOTAL", "None": "TOTAL"}).fillna("TOTAL")
    result["store"] = result["store"].replace({"nan": "ALL", "None": "ALL"}).fillna("ALL")
    result["price"] = result["price"].fillna(1.0).clip(lower=0)
    result["discount"] = result["discount"].fillna(0).clip(0, 100)

    # sort=False avoids an extra sort during grouping; the final sort below
    # establishes the required stable output order.
    result = (
        result.groupby(["product", "store", "date"], as_index=False, sort=False)
        .agg(quantity=("quantity", "sum"), price=("price", "mean"), discount=("discount", "mean"))
        .sort_values(["product", "store", "date"], kind="mergesort")
        .reset_index(drop=True)
    )

    if result["date"].nunique() < 3:
        raise ValueError("Invalid dataset: at least 3 different time points are required for forecasting.")

    metadata = {
        "date_column": date_col,
        "demand_column": demand_col,
        "product_column": product_col,
        "store_column": store_col,
        "price_column": price_col,
        "discount_column": discount_col,
        "rows": len(result),
        "products": int(result["product"].nunique()),
        "stores": int(result["store"].nunique()),
        "start_date": result["date"].min().strftime("%Y-%m-%d"),
        "end_date": result["date"].max().strftime("%Y-%m-%d"),
    }

    return result, metadata
