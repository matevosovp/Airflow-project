from collections.abc import Iterable

import pandas as pd

BOOLEAN_COLUMNS = ("is_apartment", "studio", "has_elevator")
MEDIAN_FEATURE_COLUMNS = (
    "floor",
    "kitchen_area",
    "living_area",
    "total_area",
    "build_year",
    "latitude",
    "longitude",
    "ceiling_height",
    "flats_count",
    "floors_total",
)
CLIP_COLUMNS = ("price", "total_area", "kitchen_area", "living_area")
REQUIRED_COLUMNS = frozenset(
    {"flat_id", "price", "rooms", "total_area", "kitchen_area", "living_area"}
)


def _require_columns(columns: Iterable[str]) -> None:
    missing = REQUIRED_COLUMNS.difference(columns)
    if missing:
        raise ValueError(
            "Dataset is missing required columns: " + ", ".join(sorted(missing))
        )


def _clip_iqr(series: pd.Series) -> pd.Series:
    values = series.dropna()
    if len(values) < 4:
        return series

    q1, q3 = values.quantile([0.25, 0.75])
    iqr = q3 - q1
    if pd.isna(iqr) or iqr <= 0:
        return series

    return series.clip(lower=q1 - 1.5 * iqr, upper=q3 + 1.5 * iqr)


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Return a validated, model-ready copy of a real-estate dataset.

    Identifiers and the target are never imputed. Missing numeric feature values
    are filled only when a finite median is available.
    """

    _require_columns(df.columns)
    result = df.copy()

    result = result.loc[result["flat_id"].notna()]
    result = result.drop_duplicates(subset=["flat_id"], keep="first")

    for column in BOOLEAN_COLUMNS:
        if column in result.columns:
            result[column] = (
                result[column].astype("boolean").fillna(False).astype(bool)
            )

    result = result.loc[result["price"].notna() & (result["price"] > 0)]
    result = result.loc[result["rooms"].notna() & (result["rooms"] > 0)].copy()

    for column in MEDIAN_FEATURE_COLUMNS:
        if column not in result.columns or not result[column].isna().any():
            continue
        median = result[column].median()
        if pd.notna(median):
            result[column] = result[column].fillna(median)

    positive_area = (
        (result["total_area"] > 0)
        & (result["kitchen_area"] > 0)
        & (result["living_area"] > 0)
    )
    result = result.loc[positive_area].copy()

    area_consistency = (
        (result["kitchen_area"] <= result["total_area"])
        & (result["living_area"] <= result["total_area"])
    )
    result = result.loc[area_consistency].copy()

    if {"floor", "floors_total"}.issubset(result.columns):
        valid_floor = (
            result["floor"].isna()
            | result["floors_total"].isna()
            | (
                (result["floor"] >= 0)
                & (result["floors_total"] > 0)
                & (result["floor"] <= result["floors_total"])
            )
        )
        result = result.loc[valid_floor].copy()

    for column in CLIP_COLUMNS:
        result[column] = _clip_iqr(result[column])

    final_consistency = (
        (result["kitchen_area"] <= result["total_area"])
        & (result["living_area"] <= result["total_area"])
    )
    return result.loc[final_consistency].reset_index(drop=True)
