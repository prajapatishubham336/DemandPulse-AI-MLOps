
import hashlib
import threading
from collections import OrderedDict

import numpy as np
import pandas as pd

from .preprocessing import prepare_data
from .feature_engineering import create_features
from .segmentation import classify_demand
from .tuning import tune_models


# TRAINED MODEL CACHE

_TRAINED_CACHE = OrderedDict()
_CACHE_LOCK = threading.Lock()
_MAX_CACHED_MODELS = 2


def _history_key(history):
    """
    Generate a unique cache key from the complete input history.
    A change in the data creates a different key.
    """
    frame = history.copy().reset_index(drop=True)
    digest = hashlib.sha256()
    digest.update("|".join(map(str, frame.columns)).encode("utf-8"))
    digest.update("|".join(map(str, frame.dtypes)).encode("utf-8"))
    digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    return digest.hexdigest()

# FREQUENCY DETECTION
def infer_frequency(dates):
    dates = (pd.Series(pd.to_datetime(dates)).sort_values().drop_duplicates())

    if len(dates) < 3:
        return pd.offsets.Day(1)
    freq = pd.infer_freq(dates)

    if freq:
        try:
            return pd.tseries.frequencies.to_offset(freq)
        except Exception:
            pass

    diffs = (dates.diff().dt.total_seconds().dropna() / 86400)
    median_days = float(diffs.median())

    if median_days <= 1.5:
        return pd.offsets.Day(1)

    if median_days <= 8:
        return pd.offsets.Week(1)

    if median_days <= 32:
        return pd.offsets.MonthBegin(1)

    return pd.offsets.Day(
        max(1, round(median_days))
    )

# FEATURE COLUMNS
def get_feature_columns(data):
    excluded = {
        "date",
        "quantity",
        "product",
        "store",
        "price",
        "discount"
    }

    return [
        col
        for col in data.columns
        if (
            col not in excluded
            and pd.api.types.is_numeric_dtype(data[col])
        )
    ]

# PREPARE TRAINING DATA
def prepare_training_data(history):
    data = prepare_data(history.copy())
    features = create_features(data)
    feature_cols = get_feature_columns(features)

    if not feature_cols:
        raise ValueError("Not enough usable forecasting features.")

    X = (features[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0))
    y = (pd.to_numeric(features["quantity"], errors="coerce").fillna(0))

    return data, features, X, y, feature_cols


# TRAIN FORECASTER — ORIGINAL TRAINING LOGIC
def train_forecaster(history):
    data, features, X, y, feature_cols = (prepare_training_data(history))

    # Keep the original model tuning and selection.
    training = tune_models(X, y)
    best_model_name = training["best_model"]
    best_model = training["models"][best_model_name]
    fitted = best_model.predict(X)
    residuals = y.values - fitted
    if len(residuals) >= 5:
        lower_error = float(np.quantile(residuals, 0.10))
        upper_error = float(np.quantile(residuals, 0.90))

    else:
        error = (float(np.std(residuals)) if len(residuals) else 0)
        lower_error = -error
        upper_error = error

    segment = classify_demand(data["quantity"].values)

    return {
        "data": data,
        "features": features,
        "model": best_model,
        "model_name": best_model_name,
        "feature_cols": feature_cols,
        "model_metrics": training["metrics"],
        "lower_error": lower_error,
        "upper_error": upper_error,
        "segment": segment
    }

# GET TRAINED MODEL — CACHED
def get_cached_forecaster(history):
    key = _history_key(history)

    # Protect cache access and prevent duplicate training
    # for the same history within this application process.
    with _CACHE_LOCK:
        if key in _TRAINED_CACHE:
            _TRAINED_CACHE.move_to_end(key)
            print("Forecast model cache: HIT")
            return _TRAINED_CACHE[key]

        print("Forecast model cache: MISS - training model")

        # Use the original training procedure unchanged.
        trained = train_forecaster(history)
        _TRAINED_CACHE[key] = trained
        _TRAINED_CACHE.move_to_end(key)
        while len(_TRAINED_CACHE) > _MAX_CACHED_MODELS:
            _TRAINED_CACHE.popitem(last=False)

        return trained

# RECURSIVE FORECAST
def recursive_forecast(history, horizon=30):
    if horizon not in [7, 30, 60, 90]:
        horizon = int(horizon)

    # CHANGE: use cached training instead of retraining every time.
    trained = get_cached_forecaster(history)
    data = trained["data"].copy()
    model = trained["model"]
    feature_cols = trained["feature_cols"]
    freq = infer_frequency(data["date"])
    working = data.copy()
    forecasts = []
    lower_bounds = []
    upper_bounds = []
    forecast_dates = []

    last_date = pd.to_datetime(working["date"].max())

    last_price = (
        float(working["price"].iloc[-1])
        if "price" in working.columns
        else 1.0
    )

    last_discount = (
        float(working["discount"].iloc[-1])
        if "discount" in working.columns
        else 0.0
    )

    for _ in range(horizon):
        next_date = last_date + freq
        new_row = pd.DataFrame([{
            "date": next_date,
            "quantity": 0.0,
            "product": working["product"].iloc[-1],
            "store": working["store"].iloc[-1],
            "price": last_price,
            "discount": last_discount
        }])

        temp = pd.concat([working, new_row], ignore_index=True)
        temp_features = create_features(temp)

        X_next = (
            temp_features.iloc[[-1]][feature_cols]
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
        )

        prediction = float(model.predict(X_next)[0])
        prediction = max(0.0, prediction)
        lower = max(0.0,prediction + trained["lower_error"])
        upper = max(prediction, prediction + trained["upper_error"])

        forecasts.append(prediction)
        lower_bounds.append(lower)
        upper_bounds.append(upper)
        forecast_dates.append(next_date)
        new_row.loc[0, "quantity"] = prediction
        working = pd.concat([working, new_row], ignore_index=True)
        last_date = next_date

    forecast_df = pd.DataFrame({
        "date": forecast_dates,
        "forecast": forecasts,
        "lower": lower_bounds,
        "upper": upper_bounds
    })

    best_metrics = trained["model_metrics"].get(trained["model_name"], {})
    return {
        "model": trained["model_name"],
        "segment": trained["segment"],
        "forecast": forecast_df,
        "model_metrics": trained["model_metrics"],
        "selected_metrics": {
            "WAPE": best_metrics.get("WAPE", 0),
            "MAE": best_metrics.get("MAE", 0),
            "RMSE": best_metrics.get("RMSE", 0)
        },
        "history": data,
        "frequency": str(freq),
        "rows_used": len(data)
    }