import os
import requests


def log_telegram_response(action, response):
    print(f"[telegram] {action} status: {response.status_code}")

    if not response.ok:
        print(f"[telegram] {action} response: {response.text}")


def get_telegram_credentials():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    missing = []

    if not bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")

    if not chat_id:
        missing.append("TELEGRAM_CHAT_ID")

    if missing:
        raise RuntimeError(
            "Configurazione Telegram mancante: "
            + ", ".join(missing)
            + ". Aggiungi questi valori nei GitHub Secrets."
        )

    return bot_token, chat_id


def has_telegram_credentials():
    return bool(
        os.environ.get("TELEGRAM_BOT_TOKEN")
        and os.environ.get("TELEGRAM_CHAT_ID")
    )


def send_telegram(text, chat_id=None):
    bot_token, default_chat_id = get_telegram_credentials()
    target_chat_id = chat_id or default_chat_id

    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data={
            "chat_id": target_chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    log_telegram_response("sendMessage", response)

    response.raise_for_status()


def send_telegram_photo(image_path, caption=None, chat_id=None):
    bot_token, default_chat_id = get_telegram_credentials()
    target_chat_id = chat_id or default_chat_id

    with open(image_path, "rb") as image_file:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendPhoto",
            data={
                "chat_id": target_chat_id,
                "caption": caption or "",
            },
            files={
                "photo": image_file,
            },
            timeout=60,
        )

    log_telegram_response("sendPhoto", response)

    response.raise_for_status()


def set_telegram_commands(commands):
    bot_token, _ = get_telegram_credentials()

    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/setMyCommands",
        json={
            "commands": commands,
        },
        timeout=30,
    )

    log_telegram_response("setMyCommands", response)

    response.raise_for_status()
