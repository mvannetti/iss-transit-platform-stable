import os
import time

from core.settings import get_settings
from core.astronomy import find_events, group_best
from core.i18n import t
from core.messages import build_message, build_photo_caption
from core.telegram_utils import (
    get_telegram_credentials,
    has_telegram_credentials,
    send_telegram,
    send_telegram_photo,
)
from core.graphics import create_transit_image


def log_run(message):
    print(f"[run] {message}")


def print_run_summary(
    *,
    run_type,
    status,
    settings,
    diagnostics=None,
    stats=None,
    transits=None,
    close_approaches=None,
    png_sent=0,
    elapsed_seconds=0,
):
    diagnostics = diagnostics or {}
    stats = stats or {}
    transits = transits or []
    close_approaches = close_approaches or []
    active_satellites = settings.get("enabled_satellites") or ["catalog default"]
    active_targets = list(stats) if stats else ["unknown"]

    lines = [
        "================ RUN SUMMARY ================",
        f"type: {run_type}",
        f"status: {status}",
        f"satellites: {', '.join(active_satellites)}",
        f"targets: {', '.join(active_targets)}",
        f"coarse_hits: {diagnostics.get('coarse_hits', 'unknown')}",
        f"refined_hits: {diagnostics.get('fine_centers', 'unknown')}",
        f"final_events: {len(transits)}",
        f"close_approaches: {len(close_approaches)}",
        f"png_sent: {png_sent}",
        f"duration_seconds: {elapsed_seconds:.1f}",
        "=============================================",
    ]

    for line in lines:
        log_run(line)


def execute_transit_run(settings, chat_id=None):
    start_time = time.monotonic()
    run_type = "telegram_manual" if chat_id is not None else "daily"
    transits = []
    close_approaches = []
    stats = {}
    diagnostics = {}
    png_sent = 0
    status = "error"

    log_run("Starting transit search")
    log_run(
        "Configuration loaded: "
        f"radius={settings['radius_km']} km, "
        f"search_hours={settings['search_hours']}, "
        f"language={settings.get('language', 'it')}"
    )
    active_satellites = settings.get("enabled_satellites")
    log_run(
        "Active satellites: "
        + (", ".join(active_satellites) if active_satellites else "catalog default")
    )

    try:
        transits, close_approaches, stats, diagnostics = find_events(
            settings
        )

        log_run(
            "Search completed: "
            f"coarse_hits={diagnostics['coarse_hits']}, "
            f"fine_centers={diagnostics['fine_centers']}, "
            f"transits={len(transits)}, "
            f"close_approaches={len(close_approaches)}"
        )

        message = build_message(
            settings,
            transits,
            close_approaches,
            stats,
            diagnostics,
        )

        log_run("Sending Telegram report message")
        send_telegram(message, chat_id=chat_id)

        grouped_transits = group_best(transits, 60)
        log_run(f"Grouped transit PNGs to send: {len(grouped_transits)}")

        for i, event in enumerate(grouped_transits, 1):
            filename = f"transit_{i}.png"

            try:
                log_run(
                    "Creating transit PNG "
                    f"{i}/{len(grouped_transits)} for "
                    f"{event['satellite_name']} -> {event['name']}"
                )
                create_transit_image(event, filename, settings)

                caption = build_photo_caption(settings, event)

                log_run(f"Sending Telegram PNG {i}/{len(grouped_transits)}")
                send_telegram_photo(filename, caption, chat_id=chat_id)
                png_sent += 1
            finally:
                if os.path.exists(filename):
                    os.remove(filename)
                    log_run(f"Removed local PNG {filename}")

        status = "success" if transits or close_approaches else "no_events"
    finally:
        elapsed_seconds = time.monotonic() - start_time
        print_run_summary(
            run_type=run_type,
            status=status,
            settings=settings,
            diagnostics=diagnostics,
            stats=stats,
            transits=transits,
            close_approaches=close_approaches,
            png_sent=png_sent,
            elapsed_seconds=elapsed_seconds,
        )



def main():
    settings = None

    try:
        log_run("Loading settings")
        settings = get_settings()
        get_telegram_credentials()
        execute_transit_run(settings)

    except Exception as error:
        log_run(f"Run failed: {type(error).__name__}: {error}")
        error_message = t(
            settings,
            "runtime.error",
            error_type=type(error).__name__,
            error=error,
        )

        if has_telegram_credentials():
            try:
                send_telegram(error_message)
            except Exception as telegram_error:
                print(
                    "Impossibile inviare la notifica di errore su Telegram: "
                    f"{type(telegram_error).__name__}: {telegram_error}"
                )
                print(error_message)
        else:
            print(error_message)

        raise


if __name__ == "__main__":
    main()
