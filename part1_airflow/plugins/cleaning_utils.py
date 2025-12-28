import numpy as np
import pandas as pd


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "flat_id" in df.columns:
        df = df.drop_duplicates(subset=["flat_id"], keep="first")
    else:
        df = df.drop_duplicates(keep="first")

    for c in ["is_apartment", "studio", "has_elevator"]:
        if c in df.columns:
            df[c] = df[c].fillna(False).astype(bool)

    num_cols = df.select_dtypes(include=["number"]).columns
    for c in num_cols:
        if df[c].isna().any():
            df[c] = df[c].fillna(df[c].median())

    for c in ["price", "total_area", "kitchen_area", "living_area"]:
        if c in df.columns:
            df = df[df[c] > 0]

    if "rooms" in df.columns:
        df = df[df["rooms"] > 0]

    clip_cols = [c for c in ["price", "total_area", "kitchen_area", "living_area"] if c in df.columns]
    for c in clip_cols:
        x = df[c].to_numpy()
        q1, q3 = np.percentile(x, [25, 75])
        iqr = q3 - q1
        lo = q1 - 1.5 * iqr
        hi = q3 + 1.5 * iqr
        df[c] = df[c].clip(lo, hi)

    return df
