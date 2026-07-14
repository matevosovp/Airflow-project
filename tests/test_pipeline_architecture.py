from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_raw_sql_uses_validated_atomic_swap() -> None:
    source = read("part1_airflow/plugins/real_estate_sql.py")

    assert "SELECT *" not in source
    assert "UPDATE " not in source
    assert source.index("CREATE TABLE {RAW_STAGING_TABLE}") < source.index(
        "DROP TABLE IF EXISTS {RAW_TABLE}"
    )
    assert "ALTER TABLE {RAW_STAGING_TABLE}" in source
    assert "CREATE UNIQUE INDEX" in source
    assert "duplicate flat_id" in source


def test_clean_sql_uses_validated_atomic_swap() -> None:
    source = read("part1_airflow/plugins/real_estate_clean_sql.py")

    assert "SELECT *" not in source
    assert source.index("CREATE TABLE {CLEAN_STAGING_TABLE}") < source.index(
        "DROP TABLE IF EXISTS {CLEAN_TABLE}"
    )
    assert "ALTER TABLE {CLEAN_STAGING_TABLE}" in source
    assert "failed business-rule validation" in source


def test_dags_do_not_use_fragile_cleanup_or_shared_pickles() -> None:
    raw_dag = read("part1_airflow/dags/01_real_estate_dataset_etl.py")
    clean_dag = read("part1_airflow/dags/02_real_estate_dataset_clean.py")

    assert "all_done" not in raw_dag
    assert "cleanup" not in raw_dag
    assert "pickle" not in clean_dag
    assert "AIRFLOW_SHARED_DATA_DIR" not in clean_dag
    assert "drop_previous_table" not in clean_dag


def test_dvc_extraction_and_training_avoid_known_unsafe_patterns() -> None:
    extract = read("part2_dvc/scripts/extract_from_db.py")
    train = read("part2_dvc/scripts/train.py")

    assert "SELECT *" not in extract
    assert "URL.create" in extract
    assert "chunksize=args.chunk_size" in extract
    assert "CatBoostEncoder" not in train
    assert "OneHotEncoder" in train
