from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from config import PG_CONN_ID, RAW_DATASET
from real_estate_sql import BUILD_RAW_DATASET_SQL, VALIDATE_SOURCE_SQL
from telegram_notify import send_telegram_message, task_failure_callback


def notify_success() -> None:
    send_telegram_message("[OK] real_estate_dataset_etl успешно завершён")


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "on_failure_callback": task_failure_callback,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


with DAG(
    dag_id="real_estate_dataset_etl",
    default_args=DEFAULT_ARGS,
    description="Atomically builds the raw real-estate dataset in PostgreSQL",
    start_date=datetime(2024, 1, 1),
    schedule="@once",
    catchup=False,
    max_active_runs=1,
    tags=["part1", "raw-dataset"],
) as dag:
    validate_sources = PostgresOperator(
        task_id="validate_sources",
        postgres_conn_id=PG_CONN_ID,
        sql=VALIDATE_SOURCE_SQL,
        autocommit=False,
    )

    build_raw_dataset = PostgresOperator(
        task_id="build_raw_dataset",
        postgres_conn_id=PG_CONN_ID,
        sql=BUILD_RAW_DATASET_SQL,
        autocommit=False,
        outlets=[RAW_DATASET],
    )

    send_success_notification = PythonOperator(
        task_id="notify_success",
        python_callable=notify_success,
    )

    validate_sources >> build_raw_dataset >> send_success_notification
