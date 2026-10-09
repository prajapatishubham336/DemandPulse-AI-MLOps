from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor


def build_model(name, params=None):
    params = params or {}

    if name == "Random Forest":
        return RandomForestRegressor(
            n_estimators=params.get("n_estimators", 250),
            max_depth=params.get("max_depth", 12),
            min_samples_leaf=params.get("min_samples_leaf", 1),
            max_features=params.get("max_features", 0.8),
            random_state=42,
            n_jobs=-1
        )

    if name == "XGBoost":
        return XGBRegressor(
            n_estimators=params.get("n_estimators", 300),
            max_depth=params.get("max_depth", 6),
            learning_rate=params.get("learning_rate", 0.05),
            subsample=params.get("subsample", 0.9),
            colsample_bytree=params.get("colsample_bytree", 0.8),
            objective="reg:squarederror",
            eval_metric="rmse",
            tree_method="hist",
            random_state=42,
            n_jobs=-1
        )

    if name == "LightGBM":
        return LGBMRegressor(
            n_estimators=params.get("n_estimators", 300),
            num_leaves=params.get("num_leaves", 31),
            max_depth=params.get("max_depth", -1),
            learning_rate=params.get("learning_rate", 0.05),
            subsample=params.get("subsample", 0.9),
            colsample_bytree=params.get("colsample_bytree", 0.8),
            min_child_samples=5,
            random_state=42,
            n_jobs=-1,
            verbosity=-1
        )

    raise ValueError(f"Unknown model: {name}")


MODEL_CANDIDATES = {
    "Random Forest": [
        {
            "n_estimators": 200,
            "max_depth": 8,
            "max_features": 0.8
        },
        {
            "n_estimators": 250,
            "max_depth": 12,
            "max_features": 0.8
        },
        {
            "n_estimators": 300,
            "max_depth": 18,
            "max_features": 1.0
        }
    ],

    "XGBoost": [
        {
            "n_estimators": 250,
            "max_depth": 4,
            "learning_rate": 0.05
        },
        {
            "n_estimators": 300,
            "max_depth": 6,
            "learning_rate": 0.05
        },
        {
            "n_estimators": 300,
            "max_depth": 8,
            "learning_rate": 0.03
        }
    ],

    "LightGBM": [
        {
            "n_estimators": 250,
            "num_leaves": 31,
            "learning_rate": 0.05
        },
        {
            "n_estimators": 300,
            "num_leaves": 31,
            "max_depth": 8,
            "learning_rate": 0.03
        },
        {
            "n_estimators": 300,
            "num_leaves": 63,
            "learning_rate": 0.03
        }
    ]
}