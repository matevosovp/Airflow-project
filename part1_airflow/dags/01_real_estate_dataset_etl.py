from datetime import datetime
from airflow.datasets import Dataset
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from config import RAW_DATASET
from telegram_notify import send_telegram_message, task_failure_callback
from real_estate_sql import (
    CREATE_TABLE_SQL,
    EXTRACT_SQL,
    TRANSFORM_SQL,
    LOAD_SQL,
    CLEANUP_SQL,
)



DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "on_failure_callback": task_failure_callback,
}

with DAG(
    dag_id="real_estate_dataset_etl",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval='@once',
    catchup=False,
    tags=["part1", "stage1"],
) as dag:

    create_table = PostgresOperator(
        task_id="create_table",
        postgres_conn_id="pg_conn",
        sql=CREATE_TABLE_SQL,
    )

    extract = PostgresOperator(
        task_id="extract",
        postgres_conn_id="pg_conn",
        sql=EXTRACT_SQL,
    )

    transform = PostgresOperator(
        task_id="transform",
        postgres_conn_id="pg_conn",
        sql=TRANSFORM_SQL,
    )

    load = PostgresOperator(
        task_id="load",
        postgres_conn_id="pg_conn",
        sql=LOAD_SQL,
        outlets=[RAW_DATASET],
    )

    cleanup = PostgresOperator(
        task_id="cleanup",
        postgres_conn_id="pg_conn",
        sql=CLEANUP_SQL,
        trigger_rule="all_done",
    )

    notify_success = PythonOperator(
        task_id="notify_success",
        python_callable=lambda: send_telegram_message(
            "[OK] real_estate_dataset_etl успешно завершен"
        ),
        trigger_rule="all_success",
    )

    create_table >> extract >> transform >> load >> cleanup >> notify_success
