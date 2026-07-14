from pathlib import Path
import sys

import pandas as pd

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "part1_airflow" / "plugins"
sys.path.insert(0, str(PLUGIN_DIR))

from cleaning_utils import clean_dataset


def test_clean_dataset_removes_duplicates_and_invalid_rows() -> None:
    source = pd.DataFrame(
        [
            {
                "flat_id": 1,
                "price": 100.0,
                "total_area": 40.0,
                "kitchen_area": 10.0,
                "living_area": 25.0,
                "rooms": 2,
                "is_apartment": None,
            },
            {
                "flat_id": 1,
                "price": 999.0,
                "total_area": 40.0,
                "kitchen_area": 10.0,
                "living_area": 25.0,
                "rooms": 2,
                "is_apartment": True,
            },
            {
                "flat_id": 2,
                "price": -1.0,
                "total_area": 50.0,
                "kitchen_area": 12.0,
                "living_area": 30.0,
                "rooms": 2,
                "is_apartment": False,
            },
            {
                "flat_id": 3,
                "price": 300.0,
                "total_area": 60.0,
                "kitchen_area": 15.0,
                "living_area": 35.0,
                "rooms": 3,
                "is_apartment": False,
            },
        ]
    )

    result = clean_dataset(source)

    assert result["flat_id"].tolist() == [1, 3]
    assert bool(result.loc[result["flat_id"] == 1, "is_apartment"].iloc[0]) is False


def test_clean_dataset_fills_numeric_nulls_with_median() -> None:
    source = pd.DataFrame(
        {
            "flat_id": [1, 2, 3],
            "price": [100.0, None, 300.0],
            "total_area": [40.0, 50.0, 60.0],
            "kitchen_area": [10.0, 12.0, 14.0],
            "living_area": [20.0, 25.0, 30.0],
            "rooms": [1, 2, 3],
        }
    )

    result = clean_dataset(source)

    assert result.loc[result["flat_id"] == 2, "price"].iloc[0] == 200.0
