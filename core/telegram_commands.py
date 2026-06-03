import json
from pathlib import Path

import requests

from core.catalog import default_space_object_names
from core.config_editor import (
    MAX_RADIUS_KM,
    MAX_SEARCH_HOURS,
    update_location,
    update_radius,
    update_satellites,
    update_search_hours,
    update_language,
)
from core.i18n import get_language, t
from core.settings import get_settings
from core.telegram_utils import get_telegram_credentials, send_telegram


STATE_PATH = Path("state/telegram_state.json")


def command_registry():
    return {
        "/start": {
            "menu_key": "commands.start.menu",
            "usage_key": "commands.start.usage",
            "help_key": "commands.start.help",
            "handler": handle_start,
            "public": True,
        },
        "/help": {
            "menu_key": "commands.help.menu",
            "usage_key": "commands.help.usage",
            "help_key": "commands.help.help",
            "handler": handle_help,
            "public": True,
        },
        "/status": {
            "menu_key": "commands.status.menu",
            "usage_key": "commands.status.usage",
            "help_key": "commands.status.help",
            "handler": handle_status,
            "public": True,
        },
        "/config": {
            "menu_key": "commands.config.menu",
            "usage_key": "commands.config.usage",
            "help_key": "commands.config.help",
            "handler": handle_config,
            "public": True,
        },
        "/run": {
            "menu_key": "commands.run.menu",
            "usage_key": "commands.run.usage",
            "help_key": "commands.run.help",
            "handler": handle_run,
            "public": True,
        },
        "/setlocation": {
            "menu_key": "commands.setlocation.menu",
            "usage_key": "commands.setlocation.usage",
            "help_key": "commands.setlocation.help",
            "handler": handle_setlocation,
            "public": True,
        },
        "/setradius": {
            "menu_key": "commands.setradius.menu",
            "usage_key": "commands.setradius.usage",
            "help_key": "commands.setradius.help",
            "handler": handle_setradius,
            "public": True,
        },
        "/setsatellites": {
            "menu_key": "commands.setsatellites.menu",
            "usage_key": "commands.setsatellites.usage",
            "help_key": "commands.setsatellites.help",
            "handler": handle_setsatellites,
            "public": True,
        },
        "/setsearchhours": {
            "menu_key": "commands.setsearchhours.menu",
            "usage_key": "commands.setsearchhours.usage",
            "help_key": "commands.setsearchhours.help",
            "handler": handle_setsearchhours,
            "public": True,
        },
        "/setlanguage": {
            "menu_key": "commands.setlanguage.menu",
            "usage_key": "commands.setlanguage.usage",
            "help_key": "commands.setlanguage.help",
            "handler": handle_setlanguage,
            "public": True,
        },
    }


def public_commands():
    return [
        (command, metadata)
        for command, metadata in command_registry().items()
        if metadata.get("public", True)
    ]


def command_text_values():
    return {
        "max_radius_km": MAX_RADIUS_KM,
        "max_search_hours": MAX_SEARCH_HOURS,
    }


def build_telegram_command_menu(settings=None):
    return [
        {
            "command": command.removeprefix("/"),
            "description": t(
                settings,
                metadata["menu_key"],
                **command_text_values(),
            ),
        }
        for command, metadata in public_commands()
    ]


def build_help_response(settings):
    lines = [
        t(
            settings,
            "help.line",
            usage=t(settings, metadata["usage_key"], **command_text_values()),
            description=t(settings, metadata["help_key"], **command_text_values()),
        )
        for _command, metadata in public_commands()
    ]

    return t(settings, "help.title") + "\n" + "\n".join(lines)


def load_telegram_state():
    if not STATE_PATH.exists():
        return {"last_update_id": None}

    try:
        with STATE_PATH.open("r", encoding="utf-8") as state_file:
            state = json.load(state_file)
    except (OSError, json.JSONDecodeError):
        return {"last_update_id": None}

    if not isinstance(state, dict):
        return {"last_update_id": None}

    last_update_id = state.get("last_update_id")

    if not isinstance(last_update_id, int) or isinstance(last_update_id, bool):
        last_update_id = None

    return {"last_update_id": last_update_id}


def save_telegram_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with STATE_PATH.open("w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2)
        state_file.write("\n")


def read_telegram_updates(last_update_id=None):
    bot_token, _ = get_telegram_credentials()
    params = {}

    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    response = requests.get(
        f"https://api.telegram.org/bot{bot_token}/getUpdates",
        params=params,
        timeout=30,
    )

    print("Telegram getUpdates status:", response.status_code)
    print("Telegram getUpdates response:", response.text)

    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {payload}")

    return payload.get("result", [])


def extract_message(update):
    message = update.get("message") or update.get("edited_message")

    if not message:
        return None

    chat = message.get("chat") or {}
    text = message.get("text")

    if "id" not in chat or not isinstance(text, str):
        return None

    return {
        "update_id": update.get("update_id"),
        "chat_id": chat["id"],
        "text": text.strip(),
    }


def parse_command(text):
    if not text.startswith("/"):
        return None

    return text.split()[0].split("@")[0].lower()


def parse_args(text):
    parts = text.split(maxsplit=1)

    if len(parts) == 1:
        return ""

    return parts[1].strip()


def normalize_chat_id(chat_id):
    return str(chat_id).strip()


def is_authorized_chat(chat_id, authorized_chat_id):
    return normalize_chat_id(chat_id) == normalize_chat_id(authorized_chat_id)


def handle_start(_args, _settings, _chat_id):
    return t(_settings, "start.message")


def handle_help(_args, settings, _chat_id):
    return build_help_response(settings)


def handle_status(_args, settings, _chat_id):
    satellites = settings.get("enabled_satellites") or default_space_object_names()

    return t(
        settings,
        "status.message",
        lat=settings["lat"],
        lon=settings["lon"],
        radius_km=settings["radius_km"],
        search_hours=settings["search_hours"],
        satellites=", ".join(satellites),
    )


def handle_config(_args, settings, _chat_id):
    satellites = settings.get("enabled_satellites") or default_space_object_names()

    return t(
        settings,
        "config.message",
        lat=settings["lat"],
        lon=settings["lon"],
        radius_km=settings["radius_km"],
        search_hours=settings["search_hours"],
        coarse_grid_step_km=settings["coarse_grid_step_km"],
        fine_grid_radius_km=settings["fine_grid_radius_km"],
        fine_grid_step_km=settings["fine_grid_step_km"],
        satellites=", ".join(satellites),
        language=get_language(settings),
    )


def handle_run(_args, settings, chat_id):
    from send_telegram import execute_transit_run

    send_telegram(t(settings, "run.start"), chat_id=chat_id)

    try:
        execute_transit_run(settings, chat_id=chat_id)
    except Exception as error:
        send_telegram(
            t(
                settings,
                "run.error",
                error_type=type(error).__name__,
                error=error,
            ),
            chat_id=chat_id,
        )


def handle_setlocation(args, settings, _chat_id):
    parts = args.split()

    if len(parts) != 2:
        return t(settings, "setlocation.usage_error")

    lat, lon = update_location(parts[0], parts[1])

    return t(settings, "setlocation.updated", lat=lat, lon=lon)


def handle_setradius(args, settings, _chat_id):
    if len(args.split()) != 1:
        return t(settings, "setradius.usage_error")

    radius_km = update_radius(args)

    return t(settings, "setradius.updated", radius_km=radius_km)


def handle_setsatellites(args, settings, _chat_id):
    if not args:
        return t(settings, "setsatellites.usage_error")

    satellites = update_satellites(args)

    return t(settings, "setsatellites.updated", satellites=", ".join(satellites))


def handle_setsearchhours(args, settings, _chat_id):
    if len(args.split()) != 1:
        return t(settings, "setsearchhours.usage_error")

    search_hours = update_search_hours(args)

    return t(settings, "setsearchhours.updated", search_hours=search_hours)


def handle_setlanguage(args, settings, _chat_id):
    if len(args.split()) != 1:
        return t(settings, "setlanguage.usage_error")

    language = update_language(args)
    updated_settings = {**settings, "language": language}

    return t(updated_settings, "setlanguage.updated", language=language)


def route_command(command, args, settings, chat_id):
    registry = command_registry()
    metadata = registry.get(command)

    if not metadata:
        return t(settings, "errors.unknown_command")

    try:
        return metadata["handler"](args, settings, chat_id)
    except ValueError as error:
        translation_key = getattr(error, "translation_key", None)
        values = getattr(error, "values", {})

        if translation_key:
            error = t(settings, translation_key, **values)

        return t(settings, "errors.invalid_input", error=error)


def process_telegram_commands():
    settings = get_settings()
    _, authorized_chat_id = get_telegram_credentials()
    state = load_telegram_state()
    updates = read_telegram_updates(state["last_update_id"])
    latest_update_id = state["last_update_id"]
    processed = 0

    for update in updates:
        update_id = update.get("update_id")

        if isinstance(update_id, int):
            latest_update_id = update_id

        message = extract_message(update)

        if not message:
            continue

        command = parse_command(message["text"])

        if not command:
            continue

        if not is_authorized_chat(message["chat_id"], authorized_chat_id):
            print(
                "Comando ignorato da chat non autorizzata: "
                f"{message['chat_id']}"
            )
            send_telegram(
                t(settings, "errors.unauthorized_chat"),
                chat_id=message["chat_id"],
            )
            continue

        response = route_command(
            command,
            parse_args(message["text"]),
            settings,
            message["chat_id"],
        )

        if response:
            send_telegram(response, chat_id=message["chat_id"])
            processed += 1
            settings = get_settings()

    if latest_update_id != state["last_update_id"]:
        save_telegram_state({"last_update_id": latest_update_id})

    print(f"Comandi Telegram processati: {processed}")
