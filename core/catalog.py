SPACE_OBJECTS = {
    "ISS": {
        "id": "iss",
        "display_name": "ISS",
        "norad_id": 25544,
        "emoji": "🚀",
    },
    "Tiangong": {
        "id": "tiangong",
        "display_name": "Tiangong",
        "norad_id": 48274,
        "emoji": "🇨🇳",
    },
    "Hubble": {
        "id": "hubble",
        "display_name": "Hubble",
        "norad_id": 20580,
        "emoji": "🔭",
    },
    "BlueWalker 3": {
        "id": "bluewalker3",
        "display_name": "BlueWalker 3",
        "norad_id": 53807,
        "emoji": "📡",
        "aliases": ("bluewalker 3", "bluewalker-3"),
    },
    "Envisat": {
        "id": "envisat",
        "display_name": "Envisat",
        "norad_id": 27386,
        "emoji": "🛰️",
    },
}


def build_space_object_aliases():
    aliases = {}

    for name, metadata in SPACE_OBJECTS.items():
        values = (
            metadata["id"],
            metadata["display_name"],
            *metadata.get("aliases", ()),
        )

        for value in values:
            aliases[value.strip().lower()] = name

    return aliases


SPACE_OBJECT_ALIASES = build_space_object_aliases()

OBSERVED_BODIES = [
    {
        "id": "sun",
        "name": "Sole",
        "translation_key": "bodies.sun",
        "emoji": "☀️",
        "ephem": "sun",
        "radius_km": 696_340,
        "event_types": ("transit",),
        "close_enabled": False,
    },
    {
        "id": "moon",
        "name": "Luna",
        "translation_key": "bodies.moon",
        "emoji": "🌙",
        "ephem": "moon",
        "radius_km": 1_737.4,
        "event_types": ("transit", "close_approach"),
        "close_enabled": True,
    },
    {
        "id": "jupiter",
        "name": "Giove",
        "translation_key": "bodies.jupiter",
        "emoji": "🪐",
        "ephem": "jupiter barycenter",
        "radius_km": 69_911,
        "event_types": ("transit", "close_approach"),
        "close_enabled": True,
    },
    {
        "id": "saturn",
        "name": "Saturno",
        "translation_key": "bodies.saturn",
        "emoji": "🪐",
        "ephem": "saturn barycenter",
        "radius_km": 58_232,
        "event_types": ("transit", "close_approach"),
        "close_enabled": True,
    },
    {
        "id": "venus",
        "name": "Venere",
        "translation_key": "bodies.venus",
        "emoji": "♀️",
        "ephem": "venus",
        "radius_km": 6_051.8,
        "event_types": ("transit", "close_approach"),
        "close_enabled": True,
    },
    {
        "id": "mars",
        "name": "Marte",
        "translation_key": "bodies.mars",
        "emoji": "♂️",
        "ephem": "mars",
        "radius_km": 3_389.5,
        "event_types": ("transit", "close_approach"),
        "close_enabled": True,
    },
]

EVENT_TYPES = ("transit", "close_approach")


def default_space_object_names():
    return tuple(SPACE_OBJECTS)


def supported_space_object_ids():
    return tuple(metadata["id"] for metadata in SPACE_OBJECTS.values())


def normalize_space_object_name(value):
    if not isinstance(value, str):
        return None

    key = value.strip().lower()
    return SPACE_OBJECT_ALIASES.get(key)


def get_space_object(name):
    return SPACE_OBJECTS.get(name) or SPACE_OBJECTS.get(
        normalize_space_object_name(name)
    )


def get_body_translation_key(name):
    for body in OBSERVED_BODIES:
        if body["name"] == name:
            return body["translation_key"]

    return None
