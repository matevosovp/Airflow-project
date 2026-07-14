import logging
import os

import requests

logger = logging.getLogger(__name__)


def _get_creds() -> tuple[str, str] | None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning(
            "Telegram notifications are disabled: TELEGRAM_BOT_TOKEN or "
            "TELEGRAM_CHAT_ID is not configured"
        )
        return None
    return token, chat_id


def send_telegram_message(text: str) -> bool:
    creds = _get_creds()
    if creds is None:
        return False

    token, chat_id = creds
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to send Telegram notification")
        return False

    return True


def task_failure_callback(context) -> None:
    dag_id = context["dag"].dag_id
    task_id = context["task"].task_id
    run_id = context.get("run_id")
    exception = context.get("exception")
    send_telegram_message(
        f"[FAIL] dag={dag_id} task={task_id} run_id={run_id}\n"
        f"error={exception}"
    )
