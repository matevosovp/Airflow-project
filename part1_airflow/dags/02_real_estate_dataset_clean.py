import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator

from cleaning_utils import clean_dataset
from config import CLEAN_DATASET, RAW_DATASET
from telegram_notify import send_telegram_message, task_failure_callback

SRC_TABLE = "public.real_estate_dataset_raw"
DST_TABLE = "public.real_estate_dataset_clean"

SHARED_DATA_DIR = Path(os.getenv("AIRFLOW_SHARED_DATA_DIR", "/opt/airflow/data"))
RAW_DATA_PATH = SHARED_DATA_DIR / "real_estate_raw.pkl"
CLEAN_DATA_PATH = SHARED_DATA_DIR / "real_estate_clean.pkl"


def extract_df(**context) -> None:
    SHARED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    hook = PostgresHook(postgres_conn_id="pg_conn")
    engine = hook.get_sqlalchemy_engine()
    df = pd.read_sql(f"SELECT * FROM {SRC_TABLE}", con=engine)
    context["ti"].xcom_push(key="n_rows_raw", value=int(len(df)))
    df.to_pickle(RAW_DATA_PATH)


def transform_df(**context) -> None:
    df = pd.read_pickle(RAW_DATA_PATH)
    df_clean = clean_dataset(df)
    context["ti"].xcom_push(key="n_rows_clean", value=int(len(df_clean)))
    df_clean.to_pickle(CLEAN_DATA_PATH)


def load_df(**context) -> None:
    df_clean = pd.read_pickle(CLEAN_DATA_PATH)
    hook = PostgresHook(postgres_conn_id="pg_conn")
    engine = hook.get_sqlalchemy_engine()
    df_clean.to_sql(
        name=DST_TABLE.split(".")[-1],
        schema="public",
        con=engine,
        if_exists="replace",
        index=False,
    )
    RAW_DATA_PATH.unlink(missing_ok=True)
    CLEAN_DATA_PATH.unlink(missing_ok=True)


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "on_failure_callback": task_failure_callback,
}

with DAG(
    dag_id="real_estate_dataset_clean",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule=[RAW_DATASET],
    catchup=False,
    tags=["part1", "stage2"],
) as dag:
    check_raw_table = PostgresOperator(
        task_id="check_raw_table",
        postgres_conn_id="pg_conn",
        sql="""
        DO $$
        BEGIN
        IF to_regclass('public.real_estate_dataset_raw') IS NULL THEN
            RAISE EXCEPTION 'Таблица public.real_estate_dataset_raw не найдена. Сначала выполните DAG real_estate_dataset_etl';
        END IF;
        END $$;
        """,
    )

    drop_previous_table = PostgresOperator(
        task_id="drop_previous_table",
        postgres_conn_id="pg_conn",
        sql=f"DROP TABLE IF EXISTS {DST_TABLE};",
    )

    extract = PythonOperator(task_id="extract", python_callable=extract_df)
    transform = PythonOperator(task_id="transform", python_callable=transform_df)
    load = PythonOperator(
        task_id="load",
        python_callable=load_df,
        outlets=[CLEAN_DATASET],
    )

    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=lambda: send_telegram_message(
            "[OK] real_estate_dataset_clean успешно завершён"
        ),
        trigger_rule="all_success",
    )

    check_raw_table >> drop_previous_table >> extract >> transform >> load >> notify_success
