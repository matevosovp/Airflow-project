import os
import requests


def _get_creds():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError(
            "Не заданы TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID. "
            "Добавьте их в .env и прокиньте в контейнеры Airflow."
        )
    return token, chat_id


def send_telegram_message(text: str) -> None:
    token, chat_id = _get_creds()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)
    resp.raise_for_status()


def task_failure_callback(context):
    dag_id = context["dag"].dag_id
    task_id = context["task"].task_id
    run_id = context.get("run_id")
    exc = context.get("exception")
    send_telegram_message(
        f"[FAIL] dag={dag_id} task={task_id} run_id={run_id}\nerror={exc}"
    )
