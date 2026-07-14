from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import train_test_split

IDENTIFIER_COLUMNS = ("flat_id", "building_id")
CATEGORICAL_COLUMNS = ("building_type_int",)


def load_features_and_target(
    data_path: str,
    target: str,
) -> tuple[pd.DataFrame, pd.Series, int]:
    path = Path(data_path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    dataset = pd.read_csv(path)
    if dataset.empty:
        raise ValueError(f"Dataset is empty: {path}")
    if target not in dataset.columns:
        raise ValueError(f"Target column {target!r} is missing")

    y = pd.to_numeric(dataset[target], errors="coerce")
    if y.isna().any() or not np.isfinite(y).all():
        raise ValueError(f"Target column {target!r} contains invalid values")
    if (y <= 0).any():
        raise ValueError(f"Target column {target!r} must be strictly positive")

    columns_to_drop = [target]
    columns_to_drop.extend(
        column for column in IDENTIFIER_COLUMNS if column in dataset.columns
    )
    features = dataset.drop(columns=columns_to_drop).copy()
    if features.shape[1] == 0:
        raise ValueError("Dataset contains no usable feature columns")

    for column in CATEGORICAL_COLUMNS:
        if column in features.columns:
            features[column] = features[column].astype("Int64").astype("string")
            features[column] = features[column].fillna("__missing__")

    return features, y, len(dataset)


def split_dataset(
    features: pd.DataFrame,
    target: pd.Series,
    test_size: float,
    random_state: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")
    if len(features) < 2:
        raise ValueError("At least two rows are required for a train/validation split")

    return train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
        shuffle=True,
    )


def calculate_regression_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
    *,
    rows_total: int,
) -> dict[str, float | int]:
    return {
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
        "rows_total": int(rows_total),
        "rows_val": int(len(y_true)),
    }
