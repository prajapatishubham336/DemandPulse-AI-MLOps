
import os
import time

import numpy as np
from joblib import Parallel, delayed
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from .models import build_model, MODEL_CANDIDATES


# SPEED SETTINGS
MAX_CANDIDATES = int(os.environ.get("DP_MAX_CANDIDATES", "1"))
PARALLEL_WORKERS = int(os.environ.get("DP_PARALLEL_WORKERS", "1"))


# WAPE
def wape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denominator = np.sum(np.abs(y_true))
    if denominator == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denominator)


# METRICS
def evaluate(y_true, y_pred):
    return {
        "WAPE": round(wape(y_true, y_pred) * 100, 2),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2)
    }


# HELPERS
def _limit_threads(model, n_threads):
    """Limit model threads to avoid CPU oversubscription."""
    try:
        model.set_params(n_jobs=n_threads)
    except Exception:
        pass
    return model


def _cv_score(model_name, params, X, y, splits, n_threads):
    """Calculate time-series cross-validation WAPE."""
    fold_scores = []
    for train_idx, val_idx in splits:
        model = _limit_threads(build_model(model_name, params), n_threads)
        model.fit(X.iloc[train_idx], y[train_idx])
        predictions = model.predict(X.iloc[val_idx])
        fold_scores.append(wape(y[val_idx], predictions))
    return float(np.mean(fold_scores))


# FAST MODEL TUNING
def tune_models(X, y):
    started = time.perf_counter()
    X = X.copy()
    y = np.asarray(y, dtype=float)

    if len(X) < 10:
        return train_small_dataset(X, y)

    try:
        splits = list(TimeSeriesSplit(n_splits=2).split(X))
    except Exception:
        return train_small_dataset(X, y)

    jobs = []
    for model_name, candidates in MODEL_CANDIDATES.items():
        for params in candidates[:MAX_CANDIDATES]:
            jobs.append((model_name, params))

    if not jobs:
        return train_small_dataset(X, y)

    workers = max(1, min(PARALLEL_WORKERS, len(jobs)))
    threads_each = 1 if workers > 1 else max(1, min(2, os.cpu_count() or 1))

    try:
        scores = Parallel(n_jobs=workers, backend="threading")(
            delayed(_cv_score)(name, params, X, y, splits, threads_each)
            for name, params in jobs
        )
    except Exception as exc:
        print(f"[TUNING] Parallel execution failed: {exc}. Retrying sequentially.")
        scores = [
            _cv_score(name, params, X, y, splits, 1)
            for name, params in jobs
        ]

    per_model = {}
    for (name, params), score in zip(jobs, scores):
        if name not in per_model or score < per_model[name][0]:
            per_model[name] = (score, params)

    if not per_model:
        return train_small_dataset(X, y)

    results = {
        name: {"WAPE": round(score * 100, 2), "params": params}
        for name, (score, params) in per_model.items()
    }

    best_name = min(per_model, key=lambda name: per_model[name][0])
    best_params = per_model[best_name][1]
    final_model = build_model(best_name, best_params)
    final_model.fit(X, y)

    print(
        f"[TUNING] best={best_name} "
        f"WAPE={results[best_name]['WAPE']}% "
        f"| {len(jobs)} configs | "
        f"{time.perf_counter() - started:.1f}s"
    )

    return {
        "best_model": best_name,
        "best_params": best_params,
        "models": {best_name: final_model},
        "metrics": results
    }


# SMALL DATASET
def train_small_dataset(X, y):
    fitted_models = {}
    results = {}
    best_name = None
    best_score = float("inf")
    best_params = None

    for model_name, candidates in MODEL_CANDIDATES.items():
        if not candidates:
            continue
        params = candidates[0]
        model = build_model(model_name, params)
        model.fit(X, y)
        predictions = model.predict(X)
        metrics = evaluate(y, predictions)
        fitted_models[model_name] = model
        results[model_name] = {
            "WAPE": metrics["WAPE"],
            "MAE": metrics["MAE"],
            "RMSE": metrics["RMSE"],
            "params": params
        }

        score = metrics["WAPE"] / 100
        if score < best_score:
            best_score = score
            best_name = model_name
            best_params = params

    if best_name is None:
        raise ValueError("No model candidates are configured.")

    return {
        "best_model": best_name,
        "best_params": best_params,
        "models": fitted_models,
        "metrics": results
    }