from pathlib import Path
import pandas as pd


DATE_ALIASES = [
    "date",
    "datetime",
    "timestamp",
    "day",
    "ds",
    "period",
]

DEMAND_ALIASES = [
    "quantity",
    "demand",
    "sales",
    "units",
    "units_sold",
    "qty",
    "volume",
    "y",
]

PRODUCT_ALIASES = [
    "product",
    "product_id",
    "sku",
    "item",
    "item_id",
    "store_product",
]

PRICE_ALIASES = [
    "price",
    "unit_price",
    "selling_price",
    "sales_price",
]

DISCOUNT_ALIASES = [
    "discount",
    "discount_pct",
    "discount_percent",
]

HOLIDAY_ALIASES = [
    "holiday",
    "is_holiday",
    "holiday_flag",
]


def normalize_column_name(column):
    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def normalize_columns(df):
    df = df.copy()
    df.columns = [normalize_column_name(c) for c in df.columns]
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


def load_sales_file(file_path):
    path = Path(file_path)

    if not path.exists():
        raise ValueError("Uploaded file was not found.")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)

    elif suffix == ".xlsx":
        df = pd.read_excel(path, engine="openpyxl")

    elif suffix == ".xls":
        df = pd.read_excel(path)

    else:
        raise ValueError(
            "Unsupported file format. Please upload CSV or Excel (.xlsx/.xls)."
        )

    if df.empty:
        raise ValueError("The uploaded file is empty.")

    df = normalize_columns(df)

    date_col = find_column(df.columns, DATE_ALIASES)
    demand_col = find_column(df.columns, DEMAND_ALIASES)
    product_col = find_column(df.columns, PRODUCT_ALIASES)

    if date_col is None:
        raise ValueError(
            "Could not detect a date column. "
            "Use a column such as date, datetime, timestamp or ds."
        )

    if demand_col is None:
        raise ValueError(
            "Could not detect a demand/sales column. "
            "Use a column such as quantity, demand, sales, units or qty."
        )

    result = pd.DataFrame()

    result["date"] = pd.to_datetime(
        df[date_col],
        errors="coerce"
    )

    result["quantity"] = pd.to_numeric(
        df[demand_col],
        errors="coerce"
    )

    if product_col:
        result["product"] = (
            df[product_col]
            .astype(str)
            .str.strip()
            .replace({"nan": "TOTAL"})
        )
    else:
        result["product"] = "TOTAL"

    price_col = find_column(df.columns, PRICE_ALIASES)
    discount_col = find_column(df.columns, DISCOUNT_ALIASES)
    holiday_col = find_column(df.columns, HOLIDAY_ALIASES)

    if price_col:
        result["price"] = pd.to_numeric(
            df[price_col],
            errors="coerce"
        )
    else:
        result["price"] = 1.0

    if discount_col:
        result["discount"] = pd.to_numeric(
            df[discount_col],
            errors="coerce"
        )
    else:
        result["discount"] = 0.0

    if holiday_col:
        result["holiday"] = pd.to_numeric(
            df[holiday_col],
            errors="coerce"
        )
    else:
        result["holiday"] = 0

    result = result.dropna(subset=["date", "quantity"])

    result = result[result["quantity"] >= 0]

    if result.empty:
        raise ValueError(
            "No valid demand records were found after cleaning."
        )

    result["product"] = result["product"].fillna("TOTAL")

    result["price"] = result["price"].fillna(1.0)
    result["discount"] = result["discount"].fillna(0.0)
    result["holiday"] = result["holiday"].fillna(0)

    result["discount"] = result["discount"].clip(0, 100)
    result["price"] = result["price"].clip(lower=0)

    result = (
        result
        .groupby(["product", "date"], as_index=False)
        .agg({
            "quantity": "sum",
            "price": "mean",
            "discount": "mean",
            "holiday": "max",
        })
        .sort_values(["product", "date"])
        .reset_index(drop=True)
    )

    return result


def get_products_from_upload(df):
    if "product" not in df.columns:
        return ["TOTAL"]

    products = (
        df["product"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return sorted(products)


def get_product_history_from_upload(df, product):
    if "product" not in df.columns:
        data = df.copy()
    else:
        data = df[df["product"].astype(str) == str(product)].copy()

    if data.empty:
        raise ValueError(
            f"No data found for product: {product}"
        )

    data = data.sort_values("date").reset_index(drop=True)

    return data