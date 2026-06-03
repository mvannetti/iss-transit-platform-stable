import math
from datetime import datetime, timedelta, timezone

from core.catalog import OBSERVED_BODIES, default_space_object_names, get_space_object
from skyfield.api import load, wgs84


COARSE_TIME_STEP_SECONDS = 10
REFINE_WINDOW_SECONDS = 30
REFINE_STEP_SECONDS = 1

DEFAULT_ENABLED_SATELLITES = default_space_object_names()

TLE_URL_TEMPLATE = (
    "https://celestrak.org/NORAD/elements/gp.php"
    "?CATNR={norad_id}&FORMAT=tle"
)

CLOSE_APPROACH_LIMIT_DEG = 0.25

BODIES = OBSERVED_BODIES


def log_astronomy(message):
    print(f"[astronomy] {message}")


def angular_radius_degrees(radius_km, distance_km):
    return math.degrees(math.asin(radius_km / distance_km))


def classify_transit(separation_deg, body_radius_deg):
    ratio = separation_deg / body_radius_deg

    if ratio <= 0.20:
        return "centrale"
    if ratio <= 0.90:
        return "interno al disco"
    if ratio <= 1.00:
        return "sul bordo del disco"

    return "fuori dal disco"


def generate_grid(center_lat, center_lon, radius_km, step_km):
    points = []

    for dx in range(-radius_km, radius_km + 1, step_km):
        for dy in range(-radius_km, radius_km + 1, step_km):
            distance = math.sqrt(dx**2 + dy**2)

            if distance <= radius_km:
                new_lat = center_lat + dy / 111
                new_lon = center_lon + dx / (111 * math.cos(math.radians(center_lat)))
                points.append((new_lat, new_lon, distance))

    return points


def distance_from_center_km(center_lat, center_lon, lat, lon):
    dy = (lat - center_lat) * 111
    dx = (lon - center_lon) * 111 * math.cos(math.radians(center_lat))
    return math.sqrt(dx**2 + dy**2)


def make_times(ts, start_dt, end_dt, step_seconds):
    times_dt = []
    current = start_dt

    while current <= end_dt:
        times_dt.append(current)
        current += timedelta(seconds=step_seconds)

    t = ts.utc(
        [d.year for d in times_dt],
        [d.month for d in times_dt],
        [d.day for d in times_dt],
        [d.hour for d in times_dt],
        [d.minute for d in times_dt],
        [d.second for d in times_dt],
    )

    return times_dt, t


def get_satellite_infos(enabled_satellites):
    satellite_names = enabled_satellites or DEFAULT_ENABLED_SATELLITES
    satellite_infos = []

    for name in satellite_names:
        sat_info = get_space_object(name)

        if sat_info:
            satellite_infos.append({
                "name": sat_info["display_name"],
                **sat_info,
            })
        else:
            log_astronomy(
                f"WARNING: unsupported configured satellite skipped: {name}"
            )

    if satellite_infos:
        return satellite_infos

    return [
        {"name": get_space_object(name)["display_name"], **get_space_object(name)}
        for name in DEFAULT_ENABLED_SATELLITES
    ]


def load_satellites(enabled_satellites=None):
    loaded = {}
    satellite_infos = get_satellite_infos(enabled_satellites)

    log_astronomy(
        "Loading TLE data for: "
        + ", ".join(info["name"] for info in satellite_infos)
    )

    for sat_info in satellite_infos:
        url = TLE_URL_TEMPLATE.format(norad_id=sat_info["norad_id"])
        satellites = load.tle_file(url, reload=True)

        for sat in satellites:
            loaded[sat.model.satnum] = sat

    selected = []

    for sat_info in satellite_infos:
        sat = loaded.get(sat_info["norad_id"])

        if sat:
            log_astronomy(
                f"{sat_info['name']} found: "
                f"{sat.name} / NORAD {sat.model.satnum}"
            )

            selected.append({
                "name": sat_info["name"],
                "emoji": sat_info["emoji"],
                "object": sat,
            })
        else:
            log_astronomy(
                f"WARNING: {sat_info['name']} "
                f"not found in TLE data."
            )

    if not selected:
        raise RuntimeError(
            "Nessun satellite configurato trovato nei dati TLE."
        )

    return selected


def scan_body(body_info, body, observer_ground, observer_space, iss, times_dt, t):
    iss_pos = (iss - observer_ground).at(t)
    iss_alt, _, _ = iss_pos.altaz()

    body_pos = observer_space.at(t).observe(body).apparent()
    body_alt, _, body_distance = body_pos.altaz()

    separations = iss_pos.separation_from(body_pos).degrees

    transit_candidates = []
    best_close = None

    for i, sep in enumerate(separations):
        if iss_alt.degrees[i] <= 0 or body_alt.degrees[i] <= 0:
            continue

        body_radius_deg = angular_radius_degrees(
            body_info["radius_km"],
            body_distance.km[i],
        )

        sample = {
            "name": body_info["name"],
            "emoji": body_info["emoji"],
            "time": times_dt[i],
            "sep": sep,
            "body_radius_deg": body_radius_deg,
            "iss_alt": iss_alt.degrees[i],
            "body_alt": body_alt.degrees[i],
        }

        if sep <= body_radius_deg + 0.15:
            transit_candidates.append(sample)

        if body_info["close_enabled"] and sep <= CLOSE_APPROACH_LIMIT_DEG:
            if best_close is None or sep < best_close["sep"]:
                best_close = sample

    return transit_candidates, [best_close] if best_close else []


def refine_transit(candidate, body_info, body, observer_ground, observer_space, iss, ts):
    start = candidate["time"] - timedelta(seconds=REFINE_WINDOW_SECONDS)
    end = candidate["time"] + timedelta(seconds=REFINE_WINDOW_SECONDS)

    times_dt, t = make_times(ts, start, end, REFINE_STEP_SECONDS)

    iss_pos = (iss - observer_ground).at(t)
    iss_alt, _, _ = iss_pos.altaz()

    body_pos = observer_space.at(t).observe(body).apparent()
    body_alt, _, body_distance = body_pos.altaz()

    separations = iss_pos.separation_from(body_pos).degrees

    inside_samples = []
    best = None

    for i, sep in enumerate(separations):
        if iss_alt.degrees[i] <= 0 or body_alt.degrees[i] <= 0:
            continue

        body_radius_deg = angular_radius_degrees(
            body_info["radius_km"],
            body_distance.km[i],
        )

        normalized = sep / body_radius_deg
        inside_disk = sep <= body_radius_deg

        sample = {
            "time": times_dt[i],
            "sep": sep,
            "body_radius_deg": body_radius_deg,
            "normalized": normalized,
            "iss_alt": iss_alt.degrees[i],
            "body_alt": body_alt.degrees[i],
        }

        if inside_disk:
            inside_samples.append(sample)

        if best is None or sep < best["sep"]:
            best = sample

    if not inside_samples:
        return None

    first = inside_samples[0]
    last = inside_samples[-1]
    duration_seconds = (last["time"] - first["time"]).total_seconds() + REFINE_STEP_SECONDS

    closest_pos = best["normalized"]

    if closest_pos <= 0.20:
        path_description = "passaggio vicino al centro"
    elif closest_pos <= 0.70:
        path_description = "passaggio interno al disco"
    else:
        path_description = "passaggio radente / vicino al bordo"

    return {
        "name": body_info["name"],
        "emoji": body_info["emoji"],
        "time": best["time"],
        "start_time": first["time"],
        "end_time": last["time"],
        "duration_seconds": duration_seconds,
        "sep": best["sep"],
        "body_radius_deg": best["body_radius_deg"],
        "type": classify_transit(best["sep"], best["body_radius_deg"]),
        "iss_alt": best["iss_alt"],
        "body_alt": best["body_alt"],
        "entry_pos": first["normalized"],
        "closest_pos": closest_pos,
        "exit_pos": last["normalized"],
        "path_description": path_description,
    }


def group_best(events, max_seconds):
    grouped = []

    for event in sorted(events, key=lambda e: e["time"]):
        if not grouped:
            grouped.append(event)
            continue

        last = grouped[-1]
        delta = abs((event["time"] - last["time"]).total_seconds())

        if (
            delta < max_seconds
            and event["name"] == last["name"]
            and event.get("satellite_name") == last.get("satellite_name")
        ):
            if event["sep"] < last["sep"]:
                grouped[-1] = event
        else:
            grouped.append(event)

    return grouped


def make_hit_key(body_name, event_time):
    bucket = int(event_time.timestamp() // 300)
    return f"{body_name}-{bucket}"


def make_empty_stats(bodies):
    return {
        body["name"]: {
            "emoji": body["emoji"],
            "transit_candidates": 0,
            "transits": 0,
            "close_approaches": 0,
            "close_enabled": body["close_enabled"],
        }
        for body in bodies
    }


def merge_stats(base, extra):
    for name, values in extra.items():
        base[name]["transit_candidates"] += values["transit_candidates"]
        base[name]["transits"] += values["transits"]
        base[name]["close_approaches"] += values["close_approaches"]

    return base
    
def scan_grid(settings, grid_points, bodies, earth, satellite_info, ts, times_dt, t, mode):
    satellite = satellite_info["object"]
    
    transits = []
    close_approaches = []
    hits = {}
    stats = make_empty_stats(bodies)

    for lat, lon, _ in grid_points:
        real_dist_km = distance_from_center_km(
            settings["lat"],
            settings["lon"],
            lat,
            lon,
        )

        if real_dist_km > settings["radius_km"]:
            continue

        observer_ground = wgs84.latlon(lat, lon)
        observer_space = earth + observer_ground

        for body_info in bodies:
            transit_candidates, close_candidates = scan_body(
                body_info,
                body_info["body"],
                observer_ground,
                observer_space,
                satellite,
                times_dt,
                t,
            )

            stats[body_info["name"]]["transit_candidates"] += len(transit_candidates)
            stats[body_info["name"]]["close_approaches"] += len(close_candidates)

            for close in close_candidates:
                close["lat"] = lat
                close["lon"] = lon
                close["dist_km"] = real_dist_km
                close["mode"] = mode
                close["satellite_name"] = satellite_info["name"]
                close["satellite_emoji"] = satellite_info["emoji"]
                close_approaches.append(close)

                hits[f"{satellite_info['name']}-{make_hit_key(body_info['name'], close['time'])}"] = {
                    "body_name": body_info["name"],
                    "time": close["time"],
                    "lat": lat,
                    "lon": lon,
                    "satellite_info": satellite_info,
                }

            for candidate in transit_candidates:
                hits[f"{satellite_info['name']}-{make_hit_key(body_info['name'], candidate['time'])}"] = {
                    "body_name": body_info["name"],
                    "time": candidate["time"],
                    "lat": lat,
                    "lon": lon,
                    "satellite_info": satellite_info,
                }

                refined = refine_transit(
                    candidate,
                    body_info,
                    body_info["body"],
                    observer_ground,
                    observer_space,
                    satellite,
                    ts,
                )

                if refined:
                    refined["lat"] = lat
                    refined["lon"] = lon
                    refined["dist_km"] = real_dist_km
                    refined["mode"] = mode
                    refined["satellite_name"] = satellite_info["name"]
                    refined["satellite_emoji"] = satellite_info["emoji"]
                    transits.append(refined)
                    stats[body_info["name"]]["transits"] += 1

    return transits, close_approaches, hits, stats


def find_events(settings):
    log_astronomy("Starting event search")
    ts = load.timescale()
    eph = load("de421.bsp")

    earth = eph["earth"]
    satellites = load_satellites(settings.get("enabled_satellites"))

    bodies = []
    for body_info in BODIES:
        item = body_info.copy()
        item["body"] = eph[body_info["ephem"]]
        bodies.append(item)

    log_astronomy(
        "Targets active: "
        + ", ".join(body_info["name"] for body_info in bodies)
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    end = now + timedelta(hours=settings["search_hours"])

    times_dt, t = make_times(ts, now, end, COARSE_TIME_STEP_SECONDS)

    coarse_grid = generate_grid(
        settings["lat"],
        settings["lon"],
        settings["radius_km"],
        settings["coarse_grid_step_km"],
    )

    log_astronomy(
        "Coarse grid prepared: "
        f"points={len(coarse_grid)}, "
        f"radius={settings['radius_km']} km, "
        f"step={settings['coarse_grid_step_km']} km"
    )

    all_transits = []
    all_close = []
    all_stats = None
    all_hits = {}
    
    for satellite_info in satellites:
        coarse_transits, coarse_close, hits, stats = scan_grid(
            settings,
            coarse_grid,
            bodies,
            earth,
            satellite_info,
            ts,
            times_dt,
            t,
            mode="coarse",
        )

        log_astronomy(
            f"Coarse scan {satellite_info['name']}: "
            f"transits={len(coarse_transits)}, "
            f"close_approaches={len(coarse_close)}, "
            f"hits={len(hits)}"
        )
    
        all_transits.extend(coarse_transits)
        all_close.extend(coarse_close)
        all_hits.update(hits)
    
        if all_stats is None:
            all_stats = stats
        else:
            all_stats = merge_stats(all_stats, stats)
    
    stats = all_stats
    hits = all_hits
    coarse_transits = all_transits
    coarse_close = all_close

    fine_transits = []
    fine_close = []

    refined_centers = []
    seen_centers = set()

    for hit in hits.values():
        rounded = (
            round(hit["lat"], 3),
            round(hit["lon"], 3),
            hit["satellite_info"]["name"],
            hit["body_name"],
        )

        if rounded not in seen_centers:
            seen_centers.add(rounded)
            refined_centers.append(hit)

    log_astronomy(f"Fine refinement centers: {len(refined_centers)}")

    for hit in refined_centers:
        fine_grid = generate_grid(
            hit["lat"],
            hit["lon"],
            settings["fine_grid_radius_km"],
            settings["fine_grid_step_km"],
        )

        t2, c2, _, s2 = scan_grid(
            settings,
            fine_grid,
            bodies,
            earth,
            hit["satellite_info"],
            ts,
            times_dt,
            t,
            mode="fine",
        )

        fine_transits.extend(t2)
        fine_close.extend(c2)
        stats = merge_stats(stats, s2)

    transits = fine_transits if fine_transits else coarse_transits
    close_approaches = fine_close if fine_close else coarse_close

    log_astronomy(
        "Final event counts: "
        f"transits={len(transits)}, "
        f"close_approaches={len(close_approaches)}"
    )

    diagnostics = {
        "coarse_grid_points": len(coarse_grid),
        "coarse_hits": len(hits),
        "fine_used": bool(refined_centers),
        "fine_centers": len(refined_centers),
        "coarse_step_km": settings["coarse_grid_step_km"],
        "fine_step_km": settings["fine_grid_step_km"],
        "fine_radius_km": settings["fine_grid_radius_km"],
        "satellites_checked": [
            f"{sat['emoji']} {sat['name']}"
            for sat in satellites
        ],
    }

    return transits, close_approaches, stats, diagnostics
