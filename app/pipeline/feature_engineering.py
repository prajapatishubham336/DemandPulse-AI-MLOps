import numpy as np


def create_features(df):
    data = df.copy().sort_values("date").reset_index(drop=True)

    data["day_of_week"] = data["date"].dt.dayofweek
    data["day_of_month"] = data["date"].dt.day
    data["week_of_year"] = data["date"].dt.isocalendar().week.astype(int)
    data["month"] = data["date"].dt.month
    data["quarter"] = data["date"].dt.quarter
    data["year"] = data["date"].dt.year
    data["is_weekend"] = (data["day_of_week"] >= 5).astype(int)

    data["dow_sin"] = np.sin(2 * np.pi * data["day_of_week"] / 7)
    data["dow_cos"] = np.cos(2 * np.pi * data["day_of_week"] / 7)
    data["month_sin"] = np.sin(2 * np.pi * data["month"] / 12)
    data["month_cos"] = np.cos(2 * np.pi * data["month"] / 12)

    for lag in [1, 2, 3, 7, 14, 28]:
        data[f"lag_{lag}"] = data["quantity"].shift(lag)

    shifted = data["quantity"].shift(1)

    for window in [3, 7, 14, 28]:
        data[f"rolling_mean_{window}"] = shifted.rolling(window).mean()
        data[f"rolling_std_{window}"] = shifted.rolling(window).std()
        data[f"rolling_min_{window}"] = shifted.rolling(window).min()
        data[f"rolling_max_{window}"] = shifted.rolling(window).max()

    data["trend_7"] = shifted.rolling(7).mean() - shifted.rolling(14).mean()
    data["trend_28"] = shifted.rolling(14).mean() - shifted.rolling(28).mean()
    data["price_change"] = data["price"].pct_change().replace([np.inf, -np.inf], 0).fillna(0)
    data["discount_change"] = data["discount"].diff().fillna(0)

    return data


def get_feature_columns(df):
    excluded = {"date", "quantity"}
    return [c for c in df.columns if c not in excluded and str(df[c].dtype) not in ["object", "string"]]