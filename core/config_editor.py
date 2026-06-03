import json
from pathlib import Path

from core.catalog import normalize_space_object_name, supported_space_object_ids


CONFIG_PATH = Path("config.json")
SUPPORTED_LANGUAGES = {"it", "en", "de", "fr", "rm"}
MAX_RADIUS_KM = 500
MAX_SEARCH_HOURS = 168


class ConfigValidationError(ValueError):
    def __init__(self, translation_key, **values):
        super().__init__(translation_key)
        self.translation_key = translation_key
        self.values = values


def load_editable_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    user = config["users"][0]
    return config, user


def save_config(config):
    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, indent=2)
        config_file.write("\n")


def parse_float(value, label):
    try:
        return float(value)
    except ValueError as error:
        raise ConfigValidationError(
            "validation.float_required",
            label=label,
        ) from error


def parse_positive_int(value, label, max_value):
    try:
        parsed = int(value)
    except ValueError as error:
        raise ConfigValidationError(
            "validation.integer_required",
            label=label,
        ) from error

    if parsed <= 0:
        raise ConfigValidationError("validation.greater_than_zero", label=label)

    if parsed > max_value:
        raise ConfigValidationError(
            "validation.max_value",
            label=label,
            max_value=max_value,
        )

    return parsed


def update_location(lat_value, lon_value):
    lat = parse_float(lat_value, "lat")
    lon = parse_float(lon_value, "lon")

    if not -90 <= lat <= 90:
        raise ConfigValidationError("validation.lat_range")

    if not -180 <= lon <= 180:
        raise ConfigValidationError("validation.lon_range")

    config, user = load_editable_config()
    user["lat"] = lat
    user["lon"] = lon
    save_config(config)

    return lat, lon


def update_radius(radius_value):
    radius_km = parse_positive_int(radius_value, "radius_km", MAX_RADIUS_KM)

    config, user = load_editable_config()
    user["radius_km"] = radius_km
    save_config(config)

    return radius_km


def update_search_hours(hours_value):
    search_hours = parse_positive_int(
        hours_value,
        "search_hours",
        MAX_SEARCH_HOURS,
    )

    config, user = load_editable_config()
    user["search_hours"] = search_hours
    save_config(config)

    return search_hours


def update_satellites(satellites_value):
    requested = [
        item.strip().lower()
        for item in satellites_value.split(",")
        if item.strip()
    ]

    if not requested:
        raise ConfigValidationError("validation.satellite_required")

    unknown = []

    for item in requested:
        if normalize_space_object_name(item) is None and item not in unknown:
            unknown.append(item)

    if unknown:
        allowed = ", ".join(supported_space_object_ids())
        raise ConfigValidationError(
            "validation.unsupported_satellite",
            unknown=", ".join(unknown),
            allowed=allowed,
        )

    satellites = []

    for item in requested:
        normalized = normalize_space_object_name(item)

        if normalized not in satellites:
            satellites.append(normalized)

    config, user = load_editable_config()
    user["enabled_satellites"] = satellites
    save_config(config)

    return satellites


def update_language(language_value):
    language = language_value.strip().lower()

    if language not in SUPPORTED_LANGUAGES:
        allowed = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ConfigValidationError(
            "validation.unsupported_language",
            language=language_value,
            allowed=allowed,
        )

    config, user = load_editable_config()
    user["language"] = language
    save_config(config)

    return language
