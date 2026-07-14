from pathlib import Path
import sys

import pandas as pd
import pytest

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "part1_airflow" / "plugins"
sys.path.insert(0, str(PLUGIN_DIR))

from cleaning_utils import clean_dataset


def row(flat_id: int | None, **overrides) -> dict:
    values = {
        "flat_id": flat_id,
        "price": 100.0,
        "total_area": 40.0,
        "kitchen_area": 10.0,
        "living_area": 25.0,
        "rooms": 2,
        "is_apartment": None,
    }
    values.update(overrides)
    return values


def test_clean_dataset_removes_duplicates_and_invalid_rows() -> None:
    source = pd.DataFrame(
        [
            row(1),
            row(1, price=999.0, is_apartment=True),
            row(2, price=-1.0),
            row(
                3,
                price=300.0,
                total_area=60.0,
                kitchen_area=15.0,
                living_area=35.0,
                rooms=3,
                is_apartment=False,
            ),
        ]
    )

    result = clean_dataset(source)

    assert result["flat_id"].tolist() == [1, 3]
    assert bool(result.loc[result["flat_id"] == 1, "is_apartment"].iloc[0]) is False


def test_clean_dataset_imputes_features_but_not_target() -> None:
    source = pd.DataFrame(
        [
            row(1, price=100.0, ceiling_height=2.5),
            row(2, price=200.0, ceiling_height=None),
            row(3, price=300.0, ceiling_height=3.5),
            row(4, price=None, ceiling_height=10.0),
        ]
    )

    result = clean_dataset(source)

    assert result["flat_id"].tolist() == [1, 2, 3]
    assert result.loc[result["flat_id"] == 2, "ceiling_height"].iloc[0] == 3.0


def test_clean_dataset_never_imputes_identifier() -> None:
    source = pd.DataFrame([row(None), row(2)])

    result = clean_dataset(source)

    assert result["flat_id"].tolist() == [2]


def test_clean_dataset_rejects_impossible_geometry_and_floors() -> None:
    source = pd.DataFrame(
        [
            row(1, kitchen_area=50.0),
            row(2, floor=11, floors_total=10),
            row(3, floor=5, floors_total=10),
        ]
    )

    result = clean_dataset(source)

    assert result["flat_id"].tolist() == [3]


def test_clean_dataset_handles_empty_result() -> None:
    result = clean_dataset(pd.DataFrame([row(1, price=None)]))

    assert result.empty


def test_clean_dataset_requires_core_schema() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        clean_dataset(pd.DataFrame({"flat_id": [1], "price": [100.0]}))
