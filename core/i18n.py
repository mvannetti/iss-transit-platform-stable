import json
from pathlib import Path

from core.catalog import get_body_translation_key


DEFAULT_LANGUAGE = "it"
SUPPORTED_LANGUAGES = {"it", "en", "de", "fr", "rm"}
LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"

_LOCALE_CACHE = {}


def get_language(settings):
    language = settings.get("language") if isinstance(settings, dict) else None

    if isinstance(language, str):
        language = language.strip().lower()

    if language in SUPPORTED_LANGUAGES:
        return language

    return DEFAULT_LANGUAGE


def load_locale(language):
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE

    if language not in _LOCALE_CACHE:
        path = LOCALES_DIR / f"{language}.json"

        with path.open("r", encoding="utf-8") as locale_file:
            _LOCALE_CACHE[language] = json.load(locale_file)

    return _LOCALE_CACHE[language]


def lookup(locale, key):
    value = locale.get(key)

    if isinstance(value, str):
        return value

    return None


def t(settings, key, **values):
    language = get_language(settings)
    template = lookup(load_locale(language), key)

    if template is None and language != DEFAULT_LANGUAGE:
        template = lookup(load_locale(DEFAULT_LANGUAGE), key)

    if template is None:
        return key

    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template


def body_label(settings, name):
    key = get_body_translation_key(name)

    return t(settings, key) if key else name


def localized_event_type(settings, event_type):
    key = {
        "centrale": "transit_types.central",
        "interno al disco": "transit_types.inside_disk",
        "sul bordo del disco": "transit_types.edge",
        "fuori dal disco": "transit_types.outside_disk",
    }.get(event_type)

    return t(settings, key) if key else event_type


def localized_path_description(settings, path_description):
    key = {
        "passaggio vicino al centro": "path_descriptions.near_center",
        "passaggio interno al disco": "path_descriptions.inside_disk",
        "passaggio radente / vicino al bordo": "path_descriptions.near_edge",
    }.get(path_description)

    return t(settings, key) if key else path_description
