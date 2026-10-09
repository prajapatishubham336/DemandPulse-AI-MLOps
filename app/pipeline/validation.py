import numpy as np


def wape(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    denominator = np.abs(actual).sum()
    return float(np.abs(actual - predicted).sum() / denominator * 100) if denominator else 0.0


def mae(actual, predicted):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def rmse(actual, predicted):
    return float(np.sqrt(np.mean((np.asarray(actual) - np.asarray(predicted)) ** 2)))


def evaluate(actual, predicted):
    return {"wape": round(wape(actual, predicted), 2), "mae": round(mae(actual, predicted), 2), "rmse": round(rmse(actual, predicted), 2)}


def make_splits(n, folds=3):
    if n < 12:
        return []

    horizon = max(2, min(30, n // 5))
    splits = []

    for fold in range(folds):
        test_end = n - ((folds - 1 - fold) * horizon)
        test_start = test_end - horizon
        train_end = test_start

        if train_end >= 5 and test_end <= n:
            splits.append((train_end, test_start, test_end))

    return splits