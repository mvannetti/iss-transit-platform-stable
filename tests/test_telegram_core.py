import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


sys.modules.setdefault("requests", types.SimpleNamespace(get=None))

from core import config_editor, i18n, settings as app_settings, telegram_commands
from core.catalog import OBSERVED_BODIES


def base_config():
    return {
        "users": [
            {
                "lat": 46.0,
                "lon": 9.0,
                "radius_km": 25,
                "search_hours": 72,
                "coarse_grid_step_km": 10,
                "fine_grid_radius_km": 10,
                "fine_grid_step_km": 2,
                "language": "it",
                "enabled_satellites": ["ISS"],
            }
        ]
    }


class ConfigEditorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.tempdir.name) / "config.json"
        self.config_path.write_text(json.dumps(base_config()), encoding="utf-8")
        self.original_config_path = config_editor.CONFIG_PATH
        config_editor.CONFIG_PATH = self.config_path

    def tearDown(self):
        config_editor.CONFIG_PATH = self.original_config_path
        self.tempdir.cleanup()

    def read_user(self):
        return json.loads(self.config_path.read_text(encoding="utf-8"))["users"][0]

    def test_update_language_accepts_supported_languages(self):
        for language in ["it", "en", "de", "fr", "rm"]:
            with self.subTest(language=language):
                self.assertEqual(config_editor.update_language(language.upper()), language)
                self.assertEqual(self.read_user()["language"], language)

    def test_update_language_rejects_unsupported_language(self):
        with self.assertRaises(config_editor.ConfigValidationError) as context:
            config_editor.update_language("es")

        self.assertEqual(
            context.exception.translation_key,
            "validation.unsupported_language",
        )

    def test_update_satellites_normalizes_spaces_case_and_duplicates(self):
        satellites = config_editor.update_satellites(
            " iss, ISS, tiangong , hubble, bluewalker 3, BLUEWALKER3, envisat "
        )

        self.assertEqual(
            satellites,
            ["ISS", "Tiangong", "Hubble", "BlueWalker 3", "Envisat"],
        )
        self.assertEqual(self.read_user()["enabled_satellites"], satellites)

    def test_update_satellites_rejects_unsupported_values(self):
        with self.assertRaises(config_editor.ConfigValidationError) as context:
            config_editor.update_satellites("iss, unknown, UNKNOWN")

        self.assertEqual(
            context.exception.translation_key,
            "validation.unsupported_satellite",
        )
        self.assertEqual(context.exception.values["unknown"], "unknown")

    def test_update_radius_updates_valid_value(self):
        self.assertEqual(config_editor.update_radius("42"), 42)
        self.assertEqual(self.read_user()["radius_km"], 42)

    def test_update_radius_rejects_invalid_value(self):
        for value in ["0", "-1", "9999", "abc"]:
            with self.subTest(value=value):
                with self.assertRaises(config_editor.ConfigValidationError):
                    config_editor.update_radius(value)

    def test_update_search_hours_rejects_invalid_value(self):
        for value in ["0", "-1", "9999", "abc"]:
            with self.subTest(value=value):
                with self.assertRaises(config_editor.ConfigValidationError):
                    config_editor.update_search_hours(value)

    def test_update_location_rejects_malformed_coordinates(self):
        with self.assertRaises(config_editor.ConfigValidationError):
            config_editor.update_location("north", "9.0")


class SettingsTests(unittest.TestCase):
    def test_coordinate_uses_config_when_env_is_missing_or_empty(self):
        user = {"lat": 46.0}

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                app_settings.get_coordinate(user, "USER_LAT", "lat"),
                46.0,
            )

        with mock.patch.dict("os.environ", {"USER_LAT": ""}, clear=True):
            self.assertEqual(
                app_settings.get_coordinate(user, "USER_LAT", "lat"),
                46.0,
            )

    def test_coordinate_env_override_wins_when_present(self):
        user = {"lat": 46.0}

        with mock.patch.dict("os.environ", {"USER_LAT": "47.25"}, clear=True):
            self.assertEqual(
                app_settings.get_coordinate(user, "USER_LAT", "lat"),
                47.25,
            )


class I18nTests(unittest.TestCase):
    def test_invalid_language_falls_back_to_italian(self):
        self.assertEqual(i18n.get_language({"language": "xx"}), "it")
        self.assertEqual(i18n.get_language({"language": " EN "}), "en")

    def test_missing_secondary_key_falls_back_to_italian(self):
        def fake_load_locale(language):
            if language == "it":
                return {"sample.key": "testo italiano"}
            return {}

        with mock.patch("core.i18n.load_locale", side_effect=fake_load_locale):
            self.assertEqual(
                i18n.t({"language": "en"}, "sample.key"),
                "testo italiano",
            )

    def test_missing_key_returns_key_name(self):
        self.assertEqual(i18n.t({"language": "en"}, "missing.test.key"), "missing.test.key")

    def test_new_observed_bodies_are_localized(self):
        self.assertEqual(i18n.body_label({"language": "en"}, "Venere"), "Venus")
        self.assertEqual(i18n.body_label({"language": "fr"}, "Venere"), "Vénus")
        self.assertEqual(i18n.body_label({"language": "en"}, "Marte"), "Mars")

    def test_all_observed_bodies_have_translations(self):
        for body in OBSERVED_BODIES:
            for language in ["it", "en", "de", "fr", "rm"]:
                with self.subTest(body=body["name"], language=language):
                    self.assertNotEqual(
                        i18n.t({"language": language}, body["translation_key"]),
                        body["translation_key"],
                    )


class TelegramCommandTests(unittest.TestCase):
    def test_authorized_chat_processes_command(self):
        sent_messages = []
        updates = [
            {
                "update_id": 10,
                "message": {
                    "chat": {"id": 123},
                    "text": "/help",
                },
            }
        ]

        with mock.patch("core.telegram_commands.get_settings", return_value={"language": "en"}), \
            mock.patch("core.telegram_commands.get_telegram_credentials", return_value=("token", "123")), \
            mock.patch("core.telegram_commands.load_telegram_state", return_value={"last_update_id": None}), \
            mock.patch("core.telegram_commands.save_telegram_state"), \
            mock.patch("core.telegram_commands.read_telegram_updates", return_value=updates), \
            mock.patch("core.telegram_commands.route_command", return_value="processed") as route_command, \
            mock.patch("core.telegram_commands.send_telegram", side_effect=lambda text, chat_id=None: sent_messages.append((chat_id, text))), \
            mock.patch("builtins.print"):
            telegram_commands.process_telegram_commands()

        route_command.assert_called_once()
        self.assertEqual(sent_messages, [(123, "processed")])

    def test_unauthorized_chat_blocks_command(self):
        sent_messages = []
        updates = [
            {
                "update_id": 11,
                "message": {
                    "chat": {"id": 999},
                    "text": "/run",
                },
            }
        ]

        with mock.patch("core.telegram_commands.get_settings", return_value={"language": "en"}), \
            mock.patch("core.telegram_commands.get_telegram_credentials", return_value=("token", "123")), \
            mock.patch("core.telegram_commands.load_telegram_state", return_value={"last_update_id": None}), \
            mock.patch("core.telegram_commands.save_telegram_state"), \
            mock.patch("core.telegram_commands.read_telegram_updates", return_value=updates), \
            mock.patch("core.telegram_commands.route_command") as route_command, \
            mock.patch("core.telegram_commands.send_telegram", side_effect=lambda text, chat_id=None: sent_messages.append((chat_id, text))), \
            mock.patch("builtins.print"):
            telegram_commands.process_telegram_commands()

        route_command.assert_not_called()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0][0], 999)
        self.assertIn("Unauthorized chat", sent_messages[0][1])

    def test_load_telegram_state_handles_missing_or_invalid_file(self):
        original_state_path = telegram_commands.STATE_PATH

        try:
            with tempfile.TemporaryDirectory() as tempdir:
                missing_path = Path(tempdir) / "telegram_state.json"
                telegram_commands.STATE_PATH = missing_path
                self.assertEqual(
                    telegram_commands.load_telegram_state(),
                    {"last_update_id": None},
                )

                missing_path.write_text("{bad json", encoding="utf-8")
                self.assertEqual(
                    telegram_commands.load_telegram_state(),
                    {"last_update_id": None},
                )
        finally:
            telegram_commands.STATE_PATH = original_state_path


if __name__ == "__main__":
    unittest.main()
