from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor


def build_model(name, params=None):
    params = params or {}
    if name == "Random Forest":
        return RandomForestRegressor(
            n_estimators=params.get("n_estimators", 120),
            max_depth=params.get("max_depth", 12),
            min_samples_leaf=params.get("min_samples_leaf", 1),
            max_features=params.get("max_features", 0.8),
            random_state=42,
            n_jobs=1,
        )
    if name == "XGBoost":
        return XGBRegressor(
            n_estimators=params.get("n_estimators", 120),
            max_depth=params.get("max_depth", 6),
            learning_rate=params.get("learning_rate", 0.05),
            subsample=params.get("subsample", 0.9),
            colsample_bytree=params.get("colsample_bytree", 0.8),
            objective="reg:squarederror",
            eval_metric="rmse",
            tree_method="hist",
            random_state=42,
            n_jobs=1,
        )
    if name == "LightGBM":
        return LGBMRegressor(
            n_estimators=params.get("n_estimators", 120),
            num_leaves=params.get("num_leaves", 31),
            max_depth=params.get("max_depth", -1),
            learning_rate=params.get("learning_rate", 0.05),
            subsample=params.get("subsample", 0.9),
            colsample_bytree=params.get("colsample_bytree", 0.8),
            min_child_samples=5,
            random_state=42,
            n_jobs=1,
            verbosity=-1,
            force_col_wise=True,
        )
    raise ValueError(f"Unknown model: {name}")


# Keep all original model families; use one moderate configuration per model
# to avoid expensive hyperparameter searches on a small Render instance.
MODEL_CANDIDATES = {
    "Random Forest": [{"n_estimators": 120, "max_depth": 12, "max_features": 0.8}],
    "XGBoost": [{"n_estimators": 120, "max_depth": 6, "learning_rate": 0.05}],
    "LightGBM": [{"n_estimators": 120, "num_leaves": 31, "max_depth": 8, "learning_rate": 0.05}],
}
