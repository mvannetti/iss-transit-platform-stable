from datetime import timezone
from urllib.parse import urlencode

from core.astronomy import CLOSE_APPROACH_LIMIT_DEG, group_best
from core.catalog import OBSERVED_BODIES, get_space_object
from core.i18n import body_label, localized_event_type, localized_path_description, t
from core.settings import LOCAL_TZ


def utc_to_local(dt):
    return dt.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)


def event_title(settings, event):
    satellite_emoji = event.get("satellite_emoji", "🚀")
    satellite_name = event.get("satellite_name", "ISS")

    return (
        f"{satellite_emoji} {satellite_name} → "
        f"{event['emoji']} {body_label(settings, event['name'])}"
    )


def format_number(value, decimals):
    return f"{value:.{decimals}f}"


def localized_body_list(settings, names):
    labels = [body_label(settings, name) for name in names]

    if not labels:
        return ""

    if len(labels) == 1:
        return labels[0]

    return t(
        settings,
        "report.list_with_final_or",
        items=", ".join(labels[:-1]),
        last=labels[-1],
    )


def build_photo_caption(settings, event):
    return (
        f"{event['satellite_emoji']} "
        f"{event['satellite_name']} → "
        f"{event['emoji']} {body_label(settings, event['name'])} | "
        f"{localized_event_type(settings, event['type'])} | "
        f"{event['duration_seconds']:.1f} s"
        f"\n{t(settings, 'report.caption.position', lat=event['lat'], lon=event['lon'])}"
        f"\n{t(settings, 'report.caption.maps', url=build_event_map_url(event))}"
        f"\n{t(settings, 'report.caption.transit_finder', url=build_transit_finder_url(event))}"
    )


def build_event_map_url(event):
    return f"https://www.google.com/maps?q={event['lat']:.6f},{event['lon']:.6f}"


def get_body_id(name):
    for body in OBSERVED_BODIES:
        if body["name"] == name:
            return body["id"]

    return name.lower()


def utc_isoformat(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat().replace("+00:00", "Z")


def build_transit_finder_url(event):
    satellite = get_space_object(event.get("satellite_name", ""))
    params = {
        "body": get_body_id(event["name"]),
        "lat": f"{event['lat']:.6f}",
        "lon": f"{event['lon']:.6f}",
        "utc": utc_isoformat(event["time"]),
    }

    if satellite:
        params["norad"] = satellite["norad_id"]

    return "https://satellitemap.space/transit-finder?" + urlencode(params)


def event_sort_key(event):
    return (
        event["time"],
        event.get("sep", float("inf")),
        event.get("satellite_name", ""),
        event.get("name", ""),
    )


def prioritize_events(events):
    return sorted(events, key=event_sort_key)


def build_header_text(settings):
    return (
        t(settings, "report.title")
        + "\n\n"
        + t(settings, "report.completed")
        + "\n\n"
    )


def build_no_transits_text(settings, stats):
    return (
        t(
            settings,
            "report.no_transits",
            bodies=localized_body_list(settings, stats.keys()),
            radius_km=settings["radius_km"],
            search_hours=settings["search_hours"],
        )
        + "\n\n"
    )


def build_transit_event_text(settings, index, event):
    local_time = utc_to_local(event["time"])
    start_local = utc_to_local(event["start_time"])
    end_local = utc_to_local(event["end_time"])

    return (
        f"\n{index}. {event_title(settings, event)}\n"
        f"{t(settings, 'report.fields.type', value=localized_event_type(settings, event['type']))}\n"
        f"{t(settings, 'report.fields.best_time', value=local_time.strftime('%d/%m/%Y %H:%M:%S'))}\n"
        f"{t(settings, 'report.fields.start', value=start_local.strftime('%H:%M:%S'))}\n"
        f"{t(settings, 'report.fields.end', value=end_local.strftime('%H:%M:%S'))}\n"
        f"{t(settings, 'report.fields.duration', value=format_number(event['duration_seconds'], 1))}\n"
        f"{t(settings, 'report.fields.path', value=localized_path_description(settings, event['path_description']))}\n"
        f"{t(settings, 'report.fields.entry_disk', value=format_number(event['entry_pos'], 2))}\n"
        f"{t(settings, 'report.fields.closest', value=format_number(event['closest_pos'], 2))}\n"
        f"{t(settings, 'report.fields.exit_disk', value=format_number(event['exit_pos'], 2))}\n"
        f"{t(settings, 'report.fields.distance_from_center', value=format_number(event['dist_km'], 1))}\n"
        f"{t(settings, 'report.fields.separation', value=format_number(event['sep'], 4))}\n"
        f"{t(settings, 'report.fields.satellite_altitude', value=format_number(event['iss_alt'], 1))}\n"
        f"{t(settings, 'report.fields.body_altitude', body=body_label(settings, event['name']), value=format_number(event['body_alt'], 1))}\n"
    )


def build_transits_text(settings, grouped_transits):
    text = t(settings, "report.transits_found") + "\n"

    for index, event in enumerate(grouped_transits, 1):
        text += build_transit_event_text(settings, index, event)

    return text + "\n"


def build_close_approach_event_text(settings, index, event):
    local_time = utc_to_local(event["time"])

    return (
        f"\n{index}. {event_title(settings, event)}\n"
        f"{t(settings, 'report.fields.time', value=local_time.strftime('%d/%m/%Y %H:%M:%S'))}\n"
        f"{t(settings, 'report.fields.separation', value=format_number(event['sep'], 4))}\n"
        f"{t(settings, 'report.fields.distance_from_center', value=format_number(event['dist_km'], 1))}\n"
        f"{t(settings, 'report.fields.satellite_altitude', value=format_number(event['iss_alt'], 1))}\n"
        f"{t(settings, 'report.fields.body_altitude', body=body_label(settings, event['name']), value=format_number(event['body_alt'], 1))}\n"
        f"{t(settings, 'report.fields.map_event', url=build_event_map_url(event))}\n"
    )


def build_close_approaches_text(settings, grouped_close):
    if not grouped_close:
        return ""

    text = "\n" + t(settings, "report.close_approaches_found") + "\n"

    for index, event in enumerate(grouped_close[:5], 1):
        text += build_close_approach_event_text(settings, index, event)

    return text + "\n"


def build_stats_text(settings, stats):
    text = t(settings, "report.stats.title") + "\n"

    for name, s in stats.items():
        text += f"{s['emoji']} {body_label(settings, name)}: "

        parts = []

        if s["transits"] > 0:
            parts.append(
                t(settings, "report.stats.transits", count=s["transits"])
            )
        else:
            parts.append(t(settings, "report.stats.no_transits"))

        if s["close_enabled"]:
            if s["close_approaches"] > 0:
                parts.append(
                    t(
                        settings,
                        "report.stats.close_approaches",
                        count=s["close_approaches"],
                        limit_deg=CLOSE_APPROACH_LIMIT_DEG,
                    )
                )
            else:
                parts.append(
                    t(
                        settings,
                        "report.stats.no_close_approaches",
                        limit_deg=CLOSE_APPROACH_LIMIT_DEG,
                    )
                )

        text += ", ".join(parts) + "\n"

    return text


def build_satellites_checked_text(settings, diagnostics):
    satellites_text = "\n".join(
        f"- {name}" for name in diagnostics.get("satellites_checked", [])
    )

    return (
        f"{t(settings, 'report.diagnostics.satellites_checked')}\n"
        f"{satellites_text}\n"
    )


def build_diagnostics_text(settings, diagnostics):
    if diagnostics["fine_used"]:
        mode = t(
            settings,
            "report.diagnostics.mode_fast_refined",
            coarse_step_km=diagnostics["coarse_step_km"],
            fine_step_km=diagnostics["fine_step_km"],
        )
    else:
        mode = t(
            settings,
            "report.diagnostics.mode_fast",
            coarse_step_km=diagnostics["coarse_step_km"],
        )

    return (
        f"{t(settings, 'report.diagnostics.title')}\n"
        f"{t(settings, 'report.diagnostics.mode', mode=mode)}\n"
        f"{t(settings, 'report.diagnostics.coarse_grid_points', count=diagnostics['coarse_grid_points'])}\n"
        f"{t(settings, 'report.diagnostics.coarse_hits', count=diagnostics['coarse_hits'])}\n"
        f"{t(settings, 'report.diagnostics.fine_centers', count=diagnostics['fine_centers'])}\n"
    )


def build_position_text(settings):
    return (
        "\n"
        + t(settings, "report.position.title")
        + "\n"
        + t(settings, "report.position.lat", value=f"{settings['lat']:.6f}")
        + "\n"
        + t(settings, "report.position.lon", value=f"{settings['lon']:.6f}")
        + "\n"
        + t(settings, "report.position.radius", value=settings["radius_km"])
        + "\n"
        + t(settings, "report.position.search_window", value=settings["search_hours"])
    )


def build_message(settings, transits, close_approaches, stats, diagnostics):
    grouped_transits = prioritize_events(group_best(transits, 60))
    grouped_close = prioritize_events(group_best(close_approaches, 180))

    text = build_header_text(settings)

    if not grouped_transits:
        text += build_no_transits_text(settings, stats)
    else:
        text += build_transits_text(settings, grouped_transits)

    text += build_close_approaches_text(settings, grouped_close)
    text += build_stats_text(settings, stats)
    text += "\n" + build_satellites_checked_text(settings, diagnostics)
    text += build_position_text(settings)
    text += "\n\n" + build_diagnostics_text(settings, diagnostics)

    return text
