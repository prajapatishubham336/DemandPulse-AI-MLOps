import time
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from .models import build_model, MODEL_CANDIDATES


def wape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = float(np.sum(np.abs(y_true)))
    return 0.0 if denom == 0 else float(np.sum(np.abs(y_true - y_pred)) / denom)


def evaluate(y_true, y_pred):
    return {
        "WAPE": round(wape(y_true, y_pred) * 100, 2),
        "MAE": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
    }


def tune_models(X, y):
    """Evaluate Random Forest, XGBoost and LightGBM sequentially, then refit winner."""
    started = time.perf_counter()
    X = X.copy()
    y = np.asarray(y, dtype=float)
    fitted_models, results, scores = {}, {}, {}

    if len(X) >= 10:
        splits = list(TimeSeriesSplit(n_splits=2).split(X))
        for model_name, candidates in MODEL_CANDIDATES.items():
            if not candidates:
                continue
            params = candidates[0]
            fold_scores = []
            # Sequential fitting and single-threaded models avoid CPU oversubscription.
            for train_idx, val_idx in splits:
                model = build_model(model_name, params)
                model.fit(X.iloc[train_idx], y[train_idx])
                pred = model.predict(X.iloc[val_idx])
                fold_scores.append(wape(y[val_idx], pred))
            scores[model_name] = float(np.mean(fold_scores))
            results[model_name] = {"WAPE": round(scores[model_name] * 100, 2), "params": params}
    else:
        # Small dataset fallback: fit each model once and compare its training metrics.
        for model_name, candidates in MODEL_CANDIDATES.items():
            if not candidates:
                continue
            params = candidates[0]
            model = build_model(model_name, params)
            model.fit(X, y)
            pred = model.predict(X)
            metrics = evaluate(y, pred)
            scores[model_name] = metrics["WAPE"] / 100
            results[model_name] = {**metrics, "params": params}
            fitted_models[model_name] = model

    if not scores:
        raise ValueError("No forecasting models are configured.")

    best_name = min(scores, key=scores.get)
    best_params = MODEL_CANDIDATES[best_name][0]
    if best_name not in fitted_models:
        best_model = build_model(best_name, best_params)
        best_model.fit(X, y)
        fitted_models[best_name] = best_model

    print(f"[TUNING] best={best_name} WAPE={results[best_name]['WAPE']}% | compared={list(scores)} | {time.perf_counter()-started:.1f}s")
    return {
        "best_model": best_name,
        "best_params": best_params,
        "models": {best_name: fitted_models[best_name]},
        "metrics": results,
    }
