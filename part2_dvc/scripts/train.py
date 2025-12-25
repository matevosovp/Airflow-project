import argparse
import os
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from catboost import CatBoostRegressor
from category_encoders import CatBoostEncoder


def infer_columns(X: pd.DataFrame):
    # bool -> binary
    binary_cols = X.select_dtypes(include=["bool"]).columns.tolist()

    # object -> categorical
    cat_cols = X.select_dtypes(include=["object"]).columns.tolist()

    # часто building_type_int это категориальный признак, хоть и int
    for col in ["building_type_int"]:
        if col in X.columns and col not in cat_cols and col not in binary_cols:
            cat_cols.append(col)

    # numeric = все остальные числа, кроме cat_cols и binary_cols
    num_cols = X.select_dtypes(include=["number"]).columns.tolist()
    num_cols = [c for c in num_cols if c not in cat_cols and c not in binary_cols]

    return binary_cols, cat_cols, num_cols


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--model_out", required=True)
    parser.add_argument("--test_size", type=float, required=True)
    parser.add_argument("--random_state", type=int, required=True)

    # оставляем старые имена параметров, чтобы не менять dvc.yaml/params.yaml
    parser.add_argument("--n_estimators", type=int, required=True)  # -> CatBoost iterations
    parser.add_argument("--max_depth", type=int, default=8)         # -> CatBoost depth
    parser.add_argument("--learning_rate", type=float, default=0.1)
    args = parser.parse_args()

    df = pd.read_csv(args.data)

    if args.target not in df.columns:
        raise RuntimeError(f"Target column '{args.target}' not found in dataset")

    y = df[args.target]
    X = df.drop(columns=[args.target])

    # убираем идентификаторы, чтобы не переобучаться
    for col in ["flat_id", "building_id"]:
        if col in X.columns:
            X = X.drop(columns=[col])

    # CatBoostEncoder корректнее работает, когда категориальные значения не bool
    # объектные оставляем как есть, building_type_int можно привести к string при желании
    if "building_type_int" in X.columns:
        X["building_type_int"] = X["building_type_int"].astype("Int64").astype("string")

    binary_cols, cat_cols, num_cols = infer_columns(X)

    preprocessor = ColumnTransformer(
        transformers=[
            ("binary", OneHotEncoder(drop="if_binary", handle_unknown="ignore"), binary_cols),
            ("cat", CatBoostEncoder(), cat_cols),
            ("num", StandardScaler(), num_cols),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )

    model = CatBoostRegressor(
        iterations=args.n_estimators,
        depth=args.max_depth,
        learning_rate=args.learning_rate,
        loss_function="RMSE",
        random_seed=args.random_state,
        verbose=200,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("catboost", model),
        ]
    )

    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=args.test_size, random_state=args.random_state
    )

    pipeline.fit(X_tr, y_tr)

    y_pred = pipeline.predict(X_val)

    rmse = float(mean_squared_error(y_val, y_pred, squared=False))
    mae = float(mean_absolute_error(y_val, y_pred))
    r2 = float(r2_score(y_val, y_pred))

    os.makedirs(os.path.dirname(args.model_out), exist_ok=True)
    joblib.dump(pipeline, args.model_out)

    print(f"Model saved: {args.model_out}")
    print(f"RMSE={rmse:.4f}, MAE={mae:.4f}, R2={r2:.4f}")


if __name__ == "__main__":
    main()
