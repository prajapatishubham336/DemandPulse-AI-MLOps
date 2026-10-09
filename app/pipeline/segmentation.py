import numpy as np
import pandas as pd


def classify_demand(values):
    """
    Classify demand into:
    Stable, Trending, Seasonal, or Volatile
    """

    if values is None:
        return "Stable"

    if isinstance(values, pd.Series):
        values = values.dropna().astype(float).values
    else:
        values = np.asarray(values, dtype=float)
        values = values[~np.isnan(values)]

    if len(values) < 5:
        return "Stable"

    mean_value = np.mean(values)

    if mean_value <= 0:
        return "Stable"

    # Coefficient of variation
    std_value = np.std(values)
    cv = std_value / mean_value

    # Trend strength
    x = np.arange(len(values))

    try:
        slope = np.polyfit(x, values, 1)[0]
        trend_strength = abs(slope) * len(values) / mean_value
    except Exception:
        trend_strength = 0

    # Seasonality check
    seasonal_strength = 0

    if len(values) >= 14:
        first = values[:-7]
        second = values[7:]

        if len(first) > 2 and np.std(first) > 0 and np.std(second) > 0:
            correlation = np.corrcoef(first, second)[0, 1]

            if not np.isnan(correlation):
                seasonal_strength = abs(correlation)

    # Classification
    if cv >= 0.80:
        return "Volatile"

    if seasonal_strength >= 0.60:
        return "Seasonal"

    if trend_strength >= 0.20:
        return "Trending"

    return "Stable"