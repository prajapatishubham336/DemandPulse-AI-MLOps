from pathlib import Path
import pandas as pd
import numpy as np

DATE_ALIASES = ["date", "datetime", "timestamp", "day", "week", "period", "ds", "time"]
DEMAND_ALIASES = ["sales", "demand", "quantity", "qty", "units", "units_sold", "volume", "revenue", "target", "y"]
PRODUCT_ALIASES = ["product", "product_id", "sku", "item", "item_id", "article", "category"]
STORE_ALIASES = ["store", "store_id", "location", "branch", "region", "shop"]
PRICE_ALIASES = ["price", "unit_price", "selling_price", "sales_price"]
DISCOUNT_ALIASES = ["discount", "discount_pct", "discount_percent"]


def normalize_name(name):
    return str(name).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def normalize_columns(df):
    df = df.copy()
    df.columns = [normalize_name(c) for c in df.columns]
    return df


def find_column(columns, aliases):
    columns = list(columns)
    for alias in aliases:
        if alias in columns:
            return alias
    for column in columns:
        for alias in aliases:
            if alias in column or column in alias:
                return column
    return None


def read_file(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in [".xlsx", ".xls"]:
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
        raise ValueError("Invalid dataset: a valid date/time column and demand/sales/quantity column are required.")

    result = pd.DataFrame()
    result["date"] = pd.to_datetime(df[date_col], errors="coerce")
    result["quantity"] = pd.to_numeric(df[demand_col], errors="coerce")

    result["product"] = df[product_col].astype(str) if product_col else "TOTAL"
    result["store"] = df[store_col].astype(str) if store_col else "ALL"

    result["price"] = pd.to_numeric(df[price_col], errors="coerce") if price_col else 1.0
    result["discount"] = pd.to_numeric(df[discount_col], errors="coerce") if discount_col else 0.0

    result = result.replace([np.inf, -np.inf], np.nan)
    result = result.dropna(subset=["date", "quantity"])
    result = result[result["quantity"] >= 0]

    if len(result) < 3:
        raise ValueError("Invalid dataset: not enough valid time-series demand records.")

    result["product"] = result["product"].replace({"nan": "TOTAL", "None": "TOTAL"}).fillna("TOTAL")
    result["store"] = result["store"].replace({"nan": "ALL", "None": "ALL"}).fillna("ALL")
    result["price"] = result["price"].fillna(1.0).clip(lower=0)
    result["discount"] = result["discount"].fillna(0).clip(0, 100)

    result = result.groupby(["product", "store", "date"], as_index=False).agg({"quantity": "sum", "price": "mean", "discount": "mean"})
    result = result.sort_values(["product", "store", "date"]).reset_index(drop=True)

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