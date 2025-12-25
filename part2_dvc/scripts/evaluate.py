import argparse
import json
import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--metrics_out", required=True)
    parser.add_argument("--test_size", type=float, required=True)
    parser.add_argument("--random_state", type=int, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.data)

    y = df[args.target]
    X = df.drop(columns=[args.target])

    for col in ["flat_id", "building_id"]:
        if col in X.columns:
            X = X.drop(columns=[col])

    if "building_type_int" in X.columns:
        X["building_type_int"] = X["building_type_int"].astype("Int64").astype("string")

    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state
    )

    pipeline = joblib.load(args.model)
    y_pred = pipeline.predict(X_val)

    metrics = {
        "rmse": float(mean_squared_error(y_val, y_pred, squared=False)),
        "mae": float(mean_absolute_error(y_val, y_pred)),
        "r2": float(r2_score(y_val, y_pred)),
        "rows_total": int(len(df)),
        "rows_val": int(len(X_val)),
    }

    os.makedirs(os.path.dirname(args.metrics_out), exist_ok=True)
    with open(args.metrics_out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"Metrics saved: {args.metrics_out}")
    print(metrics)


if __name__ == "__main__":
    main()
