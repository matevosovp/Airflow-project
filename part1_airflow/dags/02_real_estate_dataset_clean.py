from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from config import CLEAN_DATASET, PG_CONN_ID, RAW_DATASET
from real_estate_clean_sql import (
    BUILD_CLEAN_DATASET_SQL,
    VALIDATE_RAW_DATASET_SQL,
)
from telegram_notify import send_telegram_message, task_failure_callback


def notify_success() -> None:
    send_telegram_message("[OK] real_estate_dataset_clean успешно завершён")


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "on_failure_callback": task_failure_callback,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


with DAG(
    dag_id="real_estate_dataset_clean",
    default_args=DEFAULT_ARGS,
    description="Validates and atomically rebuilds the clean real-estate dataset",
    start_date=datetime(2024, 1, 1),
    schedule=[RAW_DATASET],
    catchup=False,
    max_active_runs=1,
    tags=["part1", "clean-dataset"],
) as dag:
    validate_raw_dataset = PostgresOperator(
        task_id="validate_raw_dataset",
        postgres_conn_id=PG_CONN_ID,
        sql=VALIDATE_RAW_DATASET_SQL,
        autocommit=False,
    )

    build_clean_dataset = PostgresOperator(
        task_id="build_clean_dataset",
        postgres_conn_id=PG_CONN_ID,
        sql=BUILD_CLEAN_DATASET_SQL,
        autocommit=False,
        outlets=[CLEAN_DATASET],
    )

    send_success_notification = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
    )

    validate_raw_dataset >> build_clean_dataset >> send_success_notification
