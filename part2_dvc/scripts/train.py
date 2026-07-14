import argparse
from pathlib import Path

import joblib
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from common import (
    calculate_regression_metrics,
    load_features_and_target,
    split_dataset,
)


def infer_columns(features: pd.DataFrame) -> tuple[list[str], list[str]]:
    categorical_columns = features.select_dtypes(
        include=["bool", "object", "string", "category"]
    ).columns.tolist()
    numeric_columns = [
        column
        for column in features.select_dtypes(include=["number"]).columns
        if column not in categorical_columns
    ]

    unsupported = set(features.columns).difference(
        categorical_columns, numeric_columns
    )
    if unsupported:
        raise ValueError(
            "Unsupported feature dtypes: " + ", ".join(sorted(unsupported))
        )

    return categorical_columns, numeric_columns


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a real-estate price model")
    parser.add_argument("--data", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--model_out", required=True)
    parser.add_argument("--test_size", type=float, required=True)
    parser.add_argument("--random_state", type=int, required=True)
    parser.add_argument("--loss_function", default="RMSE")
    parser.add_argument("--n_estimators", type=int, required=True)
    parser.add_argument("--max_depth", type=int, required=True)
    parser.add_argument("--learning_rate", type=float, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features, target, rows_total = load_features_and_target(
        args.data,
        args.target,
    )
    categorical_columns, numeric_columns = infer_columns(features)

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical_columns,
            ),
            ("numeric", "passthrough", numeric_columns),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    regressor = CatBoostRegressor(
        iterations=args.n_estimators,
        depth=args.max_depth,
        learning_rate=args.learning_rate,
        loss_function=args.loss_function,
        random_seed=args.random_state,
        allow_writing_files=False,
        verbose=200,
    )
    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ]
    )

    X_train, X_val, y_train, y_val = split_dataset(
        features,
        target,
        args.test_size,
        args.random_state,
    )
    pipeline.fit(X_train, y_train)

    metrics = calculate_regression_metrics(
        y_val,
        pipeline.predict(X_val),
        rows_total=rows_total,
    )

    model_path = Path(args.model_out)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)

    print(f"Model saved: {model_path}")
    print(
        f"RMSE={metrics['rmse']:.4f}, "
        f"MAE={metrics['mae']:.4f}, "
        f"R2={metrics['r2']:.4f}"
    )


if __name__ == "__main__":
    main()
