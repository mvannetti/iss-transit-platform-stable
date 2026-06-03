import os
import json
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Europe/Rome")


def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError as error:
        raise RuntimeError("config.json non trovato.") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"config.json non è JSON valido: {error}") from error

    if not isinstance(config, dict):
        raise RuntimeError("config.json deve contenere un oggetto JSON.")

    users = config.get("users")

    if not isinstance(users, list) or not users:
        raise RuntimeError("config.json deve contenere una lista users non vuota.")

    if not isinstance(users[0], dict):
        raise RuntimeError("config.json users[0] deve essere un oggetto.")

    return config


def get_required_number(user, key, cast):
    if key not in user:
        raise RuntimeError(f"config.json: manca il campo users[0].{key}.")

    try:
        value = cast(user[key])
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            f"config.json: users[0].{key} deve essere un numero valido."
        ) from error

    if value <= 0:
        raise RuntimeError(
            f"config.json: users[0].{key} deve essere maggiore di zero."
        )

    return value


def get_coordinate(user, env_name, config_key):
    raw_value = os.environ.get(env_name)

    if raw_value in (None, ""):
        raw_value = user.get(config_key)

    if raw_value in (None, ""):
        raise RuntimeError(
            f"Coordinata mancante: imposta users[0].{config_key} "
            f"in config.json oppure usa {env_name} come override opzionale."
        )

    try:
        return float(raw_value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            f"La coordinata users[0].{config_key}/{env_name} "
            "deve essere un numero valido."
        ) from error


def get_settings():
    user = load_config()["users"][0]
    enabled_satellites = user.get("enabled_satellites")

    if not (
        isinstance(enabled_satellites, list)
        and all(isinstance(name, str) for name in enabled_satellites)
    ):
        enabled_satellites = None

    return {
        "lat": get_coordinate(user, "USER_LAT", "lat"),
        "lon": get_coordinate(user, "USER_LON", "lon"),
        "language": user.get("language"),

        "radius_km": get_required_number(user, "radius_km", int),
        "search_hours": get_required_number(user, "search_hours", int),

        "coarse_grid_step_km": get_required_number(user, "coarse_grid_step_km", int),
        "fine_grid_radius_km": get_required_number(user, "fine_grid_radius_km", int),
        "fine_grid_step_km": get_required_number(user, "fine_grid_step_km", int),

        "enabled_satellites": enabled_satellites,
    }
