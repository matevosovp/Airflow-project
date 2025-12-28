from airflow.datasets import Dataset

PG_CONN_ID = "pg_conn"

RAW_TABLE = "public.real_estate_dataset_raw"
CLEAN_TABLE = "public.real_estate_dataset_clean"

RAW_DATASET_URI = f"postgres://{PG_CONN_ID}/{RAW_TABLE}"
CLEAN_DATASET_URI = f"postgres://{PG_CONN_ID}/{CLEAN_TABLE}"

RAW_DATASET = Dataset(RAW_DATASET_URI)
CLEAN_DATASET = Dataset(CLEAN_DATASET_URI)
