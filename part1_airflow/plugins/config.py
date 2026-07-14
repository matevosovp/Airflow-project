from airflow.datasets import Dataset

PG_CONN_ID = "pg_conn"
DB_SCHEMA = "public"

FLATS_TABLE = f"{DB_SCHEMA}.flats"
BUILDINGS_TABLE = f"{DB_SCHEMA}.buildings"

RAW_TABLE = f"{DB_SCHEMA}.real_estate_dataset_raw"
RAW_STAGING_TABLE = f"{DB_SCHEMA}.real_estate_dataset_raw_stg"
CLEAN_TABLE = f"{DB_SCHEMA}.real_estate_dataset_clean"
CLEAN_STAGING_TABLE = f"{DB_SCHEMA}.real_estate_dataset_clean_stg"

RAW_DATASET = Dataset(f"postgres://{PG_CONN_ID}/{RAW_TABLE}")
CLEAN_DATASET = Dataset(f"postgres://{PG_CONN_ID}/{CLEAN_TABLE}")
