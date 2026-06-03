import sys
import types
import unittest
from datetime import datetime, timezone


sys.modules["core.astronomy"] = types.SimpleNamespace(
    CLOSE_APPROACH_LIMIT_DEG=0.25,
    group_best=lambda events, _seconds: events,
)

from core import messages


def settings(language="en"):
    return {
        "language": language,
        "lat": 46.0,
        "lon": 9.0,
        "radius_km": 25,
        "search_hours": 72,
    }


def transit_event():
    return {
        "satellite_emoji": "🚀",
        "satellite_name": "ISS",
        "emoji": "☀️",
        "name": "Sole",
        "type": "centrale",
        "time": datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc),
        "start_time": datetime(2026, 5, 19, 11, 59, 50, tzinfo=timezone.utc),
        "end_time": datetime(2026, 5, 19, 12, 0, 10, tzinfo=timezone.utc),
        "lat": 46.123456,
        "lon": 9.123456,
        "duration_seconds": 20.0,
        "path_description": "passaggio vicino al centro",
        "entry_pos": 0.1,
        "closest_pos": 0.05,
        "exit_pos": 0.1,
        "dist_km": 4.2,
        "sep": 0.0123,
        "iss_alt": 45.0,
        "body_alt": 30.0,
    }


def shifted_transit_event(hours, satellite_name="ISS", sep=0.0123):
    event = transit_event().copy()
    event["time"] = datetime(2026, 5, 19, 12 + hours, 0, tzinfo=timezone.utc)
    event["start_time"] = datetime(2026, 5, 19, 11 + hours, 59, 50, tzinfo=timezone.utc)
    event["end_time"] = datetime(2026, 5, 19, 12 + hours, 0, 10, tzinfo=timezone.utc)
    event["satellite_name"] = satellite_name
    event["sep"] = sep
    return event


def close_approach_event():
    return {
        "satellite_emoji": "🔭",
        "satellite_name": "Hubble",
        "emoji": "🌙",
        "name": "Luna",
        "time": datetime(2026, 5, 19, 14, 0, tzinfo=timezone.utc),
        "lat": 46.234567,
        "lon": 9.234567,
        "dist_km": 5.3,
        "sep": 0.2,
        "iss_alt": 50.0,
        "body_alt": 31.0,
    }


def shifted_close_approach_event(hours, satellite_name="Hubble", sep=0.2):
    event = close_approach_event().copy()
    event["time"] = datetime(2026, 5, 19, 14 + hours, 0, tzinfo=timezone.utc)
    event["satellite_name"] = satellite_name
    event["sep"] = sep
    return event


def stats(transits=1, close_approaches=1):
    return {
        "Sole": {
            "emoji": "☀️",
            "transits": transits,
            "close_enabled": False,
            "close_approaches": 0,
        },
        "Luna": {
            "emoji": "🌙",
            "transits": 0,
            "close_enabled": True,
            "close_approaches": close_approaches,
        },
    }


def diagnostics(fine_used=True):
    return {
        "fine_used": fine_used,
        "coarse_step_km": 10,
        "fine_step_km": 2,
        "coarse_grid_points": 81,
        "coarse_hits": 3,
        "fine_centers": 1,
        "satellites_checked": [
            "🚀 ISS",
            "🇨🇳 Tiangong",
            "🔭 Hubble",
            "📡 BlueWalker 3",
            "🛰️ Envisat",
        ],
    }


class MessageBuilderTests(unittest.TestCase):
    def test_build_event_map_url(self):
        self.assertEqual(
            messages.build_event_map_url(transit_event()),
            "https://www.google.com/maps?q=46.123456,9.123456",
        )

    def test_build_position_text_contains_coordinates(self):
        text = messages.build_position_text(settings("it"))

        self.assertIn("📍 Posizione centrale:", text)
        self.assertIn("Lat: 46.000000", text)
        self.assertIn("Lon: 9.000000", text)
        self.assertIn("Raggio ricerca: 25 km", text)

    def test_build_header_text_is_not_empty(self):
        text = messages.build_header_text(settings("en"))

        self.assertIn("🚀 Transit Bot", text)
        self.assertIn("Daily check completed", text)

    def test_build_transit_event_text_contains_key_event_data(self):
        text = messages.build_transit_event_text(settings("en"), 1, transit_event())

        self.assertIn("1. 🚀 ISS", text)
        self.assertIn("Sun", text)
        self.assertIn("Type: central", text)
        self.assertIn("Duration: 20.0 s", text)
        self.assertNotIn("Event map:", text)

    def test_build_close_approach_event_text_contains_key_event_data(self):
        text = messages.build_close_approach_event_text(
            settings("en"),
            1,
            close_approach_event(),
        )

        self.assertIn("1. 🔭 Hubble", text)
        self.assertIn("Moon", text)
        self.assertIn("Separation: 0.2000°", text)
        self.assertIn("Distance from center: 5.3 km", text)
        self.assertIn("Event map: https://www.google.com/maps?q=46.234567,9.234567", text)

    def test_build_no_transits_text(self):
        text = messages.build_no_transits_text(settings("it"), stats(transits=0))

        self.assertIn("Nessun transito", text)
        self.assertIn("Sole", text)
        self.assertIn("Luna", text)
        self.assertIn("25 km", text)

    def test_build_transits_text_contains_section_and_event(self):
        text = messages.build_transits_text(settings("en"), [transit_event()])

        self.assertIn("🔹 Transits found:", text)
        self.assertIn("ISS", text)
        self.assertIn("Sun", text)

    def test_build_close_approaches_text_contains_section_and_event(self):
        text = messages.build_close_approaches_text(
            settings("en"),
            [close_approach_event()],
        )

        self.assertIn("🔭 Interesting close approaches:", text)
        self.assertIn("Hubble", text)
        self.assertIn("Moon", text)

    def test_build_close_approaches_text_empty_without_events(self):
        self.assertEqual(messages.build_close_approaches_text(settings("en"), []), "")

    def test_prioritize_events_orders_by_time_then_separation(self):
        later = shifted_transit_event(2, satellite_name="ISS", sep=0.01)
        earlier_worse = shifted_transit_event(0, satellite_name="Hubble", sep=0.2)
        earlier_better = shifted_transit_event(0, satellite_name="Tiangong", sep=0.05)

        ordered = messages.prioritize_events([later, earlier_worse, earlier_better])

        self.assertEqual(
            [event["satellite_name"] for event in ordered],
            ["Tiangong", "Hubble", "ISS"],
        )

    def test_build_message_without_transits(self):
        text = messages.build_message(
            settings("en"),
            [],
            [],
            stats(transits=0, close_approaches=0),
            diagnostics(fine_used=False),
        )

        self.assertIn("No transit", text)
        self.assertIn("Bodies checked", text)
        self.assertIn("Search diagnostics", text)

    def test_build_message_with_transit(self):
        text = messages.build_message(
            settings("en"),
            [transit_event()],
            [],
            stats(),
            diagnostics(),
        )

        self.assertIn("🔹 Transits found:", text)
        self.assertIn("ISS", text)
        self.assertIn("Sun", text)

    def test_build_message_orders_transits_before_close_approaches(self):
        text = messages.build_message(
            settings("en"),
            [shifted_transit_event(2)],
            [shifted_close_approach_event(0)],
            stats(),
            diagnostics(),
        )

        self.assertLess(
            text.index("🔹 Transits found:"),
            text.index("🔭 Interesting close approaches:"),
        )

    def test_build_message_uses_requested_section_order(self):
        text = messages.build_message(
            settings("en"),
            [transit_event()],
            [close_approach_event()],
            stats(),
            diagnostics(),
        )

        self.assertLess(
            text.index("🔭 Interesting close approaches:"),
            text.index("📋 Bodies checked:"),
        )
        self.assertIn("\n\n📋 Bodies checked:", text)
        self.assertLess(
            text.index("📋 Bodies checked:"),
            text.index("Satellites checked:"),
        )
        self.assertIn("\n\n🛰 Satellites checked:", text)
        self.assertLess(
            text.index("Satellites checked:"),
            text.index("📍 Central position:"),
        )
        self.assertLess(
            text.index("📍 Central position:"),
            text.index("🧪 Search diagnostics:"),
        )

    def test_build_message_with_close_approach(self):
        text = messages.build_message(
            settings("en"),
            [],
            [close_approach_event()],
            stats(transits=0),
            diagnostics(),
        )

        self.assertIn("🔭 Interesting close approaches:", text)
        self.assertIn("Hubble", text)
        self.assertIn("Moon", text)

    def test_build_stats_text(self):
        text = messages.build_stats_text(settings("en"), stats())

        self.assertIn("📋 Bodies checked:", text)
        self.assertIn("Sun: 1 transit(s)", text)
        self.assertIn("Moon", text)

    def test_build_diagnostics_text(self):
        text = messages.build_diagnostics_text(settings("en"), diagnostics())

        self.assertIn("🧪 Search diagnostics:", text)
        self.assertIn("Mode: fast scan 10 km + local refinement 2 km", text)

    def test_build_satellites_checked_text(self):
        text = messages.build_satellites_checked_text(settings("en"), diagnostics())

        self.assertIn("Satellites checked", text)
        self.assertIn("- 🚀 ISS", text)
        self.assertIn("- 📡 BlueWalker 3", text)

    def test_build_photo_caption(self):
        text = messages.build_photo_caption(settings("en"), transit_event())

        self.assertIn("🚀 ISS → ☀️ Sun | central | 20.0 s", text)
        self.assertIn("Position: 46.123456, 9.123456", text)
        self.assertIn("Map: https://www.google.com/maps?q=46.123456,9.123456", text)
        self.assertIn("Transit Finder: https://satellitemap.space/transit-finder?", text)
        self.assertIn("body=sun", text)
        self.assertIn("norad=25544", text)
        self.assertIn("utc=2026-05-19T12%3A00%3A00Z", text)

    def test_build_photo_caption_has_stable_line_order(self):
        lines = messages.build_photo_caption(settings("en"), transit_event()).splitlines()

        self.assertEqual(lines[0], "🚀 ISS → ☀️ Sun | central | 20.0 s")
        self.assertTrue(lines[1].startswith("Position: "))
        self.assertTrue(lines[2].startswith("Map: "))
        self.assertTrue(lines[3].startswith("Transit Finder: "))

    def test_report_language_keywords(self):
        expectations = {
            "it": "Controllo giornaliero completato",
            "en": "Daily check completed",
            "de": "Tägliche Prüfung abgeschlossen",
            "fr": "Contrôle quotidien terminé",
            "rm": "Controlla quotidiana terminada",
        }

        for language, expected in expectations.items():
            with self.subTest(language=language):
                text = messages.build_message(
                    settings(language),
                    [],
                    [],
                    stats(transits=0, close_approaches=0),
                    diagnostics(fine_used=False),
                )

                self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
