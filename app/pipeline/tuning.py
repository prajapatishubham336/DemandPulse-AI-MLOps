import time

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from .models import build_model


# Lightweight settings for Render free instance
MODEL_NAME = "LightGBM"

MODEL_PARAMS = {
    "n_estimators": 80,
    "num_leaves": 15,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.9,
    "colsample_bytree": 0.8,
}


# WAPE METRIC
def wape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    denominator = np.sum(np.abs(y_true))

    if denominator == 0:
        return 0.0

    return float(
        np.sum(np.abs(y_true - y_pred)) / denominator
    )


# MODEL EVALUATION
def evaluate(y_true, y_pred):
    return {
        "WAPE": round(wape(y_true, y_pred) * 100, 2),
        "MAE": round(
            float(mean_absolute_error(y_true, y_pred)), 2
        ),
        "RMSE": round(
            float(np.sqrt(mean_squared_error(y_true, y_pred))), 2
        ),
    }


# LIGHTWEIGHT MODEL TRAINING
def tune_models(X, y):
    started = time.perf_counter()

    X = X.copy()
    y = np.asarray(y, dtype=float)

    if len(X) == 0:
        raise ValueError("No training data available.")

    params = MODEL_PARAMS.copy()
    metrics = None

    # Time-series validation
    if len(X) >= 10:
        try:
            splitter = TimeSeriesSplit(n_splits=2)
            splits = list(splitter.split(X))

            train_idx, val_idx = splits[-1]

            validation_model = build_model(
                MODEL_NAME, params
            )

            validation_model.fit(
                X.iloc[train_idx],
                y[train_idx],
            )

            predictions = validation_model.predict(
                X.iloc[val_idx]
            )

            metrics = evaluate(
                y[val_idx],
                predictions,
            )

        except (ValueError, IndexError) as exc:
            print(
                f"[TUNING] Validation fallback: {exc}"
            )

    # Fit final model using all available history
    model = build_model(MODEL_NAME, params)
    model.fit(X, y)

    # Fallback metrics for small datasets
    if metrics is None:
        predictions = model.predict(X)
        metrics = evaluate(y, predictions)

    results = {
        MODEL_NAME: {
            **metrics,
            "params": params,
        }
    }

    elapsed = time.perf_counter() - started

    print(
        f"[TUNING] Model: {MODEL_NAME} | "
        f"WAPE: {metrics['WAPE']}% | "
        f"Time: {elapsed:.1f}s"
    )

    return {
        "best_model": MODEL_NAME,
        "best_params": params,
        "models": {
            MODEL_NAME: model,
        },
        "metrics": results,
    }


# BACKWARD-COMPATIBLE SMALL DATASET FUNCTION
def train_small_dataset(X, y):
    return tune_models(X, y)

