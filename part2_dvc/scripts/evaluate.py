import argparse
import json
from pathlib import Path

import joblib

from common import (
    calculate_regression_metrics,
    load_features_and_target,
    split_dataset,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained model")
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--metrics_out", required=True)
    parser.add_argument("--test_size", type=float, required=True)
    parser.add_argument("--random_state", type=int, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model)
    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found: {model_path}")

    features, target, rows_total = load_features_and_target(
        args.data,
        args.target,
    )
    _, X_val, _, y_val = split_dataset(
        features,
        target,
        args.test_size,
        args.random_state,
    )

    pipeline = joblib.load(model_path)
    metrics = calculate_regression_metrics(
        y_val,
        pipeline.predict(X_val),
        rows_total=rows_total,
    )

    metrics_path = Path(args.metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(f"{metrics_path}.tmp")
    temporary_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(metrics_path)

    print(f"Metrics saved: {metrics_path}")
    print(metrics)


if __name__ == "__main__":
    main()
