# ISS Transit Platform

ISS Transit Platform is a Python Telegram bot that searches for satellite transits and close approaches near selected celestial bodies. It is designed to run from GitHub Actions, so it does not need a personal server.

The bot can send a daily report, respond to Telegram commands, and update selected settings in `config.json`.

The private source repository also contains a maintainer workflow that publishes a clean stable copy to a public repository.

## Features

- Searches for visible events for ISS, Tiangong, Hubble, BlueWalker 3, and Envisat.
- Checks the Sun, Moon, Jupiter, Saturn, Venus, and Mars.
- Reports transits and close approaches when available, ordered for predictable reading.
- Sends Telegram reports with event details, coordinates, Google Maps links, diagnostics, and PNG diagrams for grouped transits.
- Writes lightweight GitHub Actions logs with a final run summary.
- Supports manual `/run` searches from Telegram.
- Supports read-only Telegram commands for status and configuration.
- Supports controlled Telegram updates to selected `config.json` fields.
- Restricts Telegram command execution to `TELEGRAM_CHAT_ID`.
- Supports Italian, English, German, French, and Romansh via `config.json`.
- Runs with GitHub Actions schedules or manual workflow dispatch.

## Repository Structure

```text
iss-transit-platform/
├─ send_telegram.py
├─ process_telegram_commands.py
├─ setup_telegram_commands.py
├─ config.json
├─ requirements.txt
├─ core/
│  ├─ astronomy.py
│  ├─ catalog.py
│  ├─ config_editor.py
│  ├─ graphics.py
│  ├─ i18n.py
│  ├─ messages.py
│  ├─ settings.py
│  ├─ telegram_commands.py
│  └─ telegram_utils.py
├─ locales/
│  ├─ it.json
│  ├─ en.json
│  ├─ de.json
│  ├─ fr.json
│  └─ rm.json
├─ tests/
├─ state/
│  └─ telegram_state.json
└─ .github/
   └─ workflows/
      ├─ daily.yml
      ├─ process-telegram-commands.yml
      └─ setup-telegram-commands.yml
```

The private source repository also contains `.github/workflows/publish-stable.yml`. That workflow is maintainer-only and is not published to the public stable repository.

## Important Files

- `send_telegram.py`: entry point for the daily/manual transit search, including run logging and final summary.
- `process_telegram_commands.py`: processes pending Telegram updates once, then exits.
- `setup_telegram_commands.py`: registers the bot command menu with Telegram.
- `core/astronomy.py`: TLE loading, grid scanning, transit detection, and close-approach detection.
- `core/catalog.py`: supported satellites, observed bodies, and event-type metadata.
- `core/messages.py`: localized report, event ordering, and caption builders.
- `core/graphics.py`: PNG transit diagram generation.
- `core/telegram_commands.py`: command registry, routing, authorization, and command handlers.
- `core/config_editor.py`: safe updates to editable config fields.
- `core/i18n.py`: translation loading, language fallback, and shared localized labels.
- `locales/*.json`: Italian, English, German, French, and Romansh translations.
- `tests/`: small regression suite for messages, i18n, Telegram command parsing, authorization, and config editing.
- `state/telegram_state.json`: last processed Telegram update ID.
- `.github/workflows/daily.yml`: daily/manual transit search.
- `.github/workflows/process-telegram-commands.yml`: scheduled/manual Telegram command processing.
- `.github/workflows/setup-telegram-commands.yml`: manual Telegram command menu setup.

## Quick Start

These steps are enough to get a fork running for the first time.

1. Fork the public stable repository:

   ```text
   https://github.com/ericcatta/iss-transit-platform-stable
   ```

2. Decide whether your fork should be private.

   If you put real coordinates in `config.json` and the fork is public, those coordinates are public too. For personal use, a private fork is recommended.

3. In Telegram, create a bot with BotFather:

   ```text
   @BotFather
   /newbot
   ```

   BotFather will give you a token. Keep it private. This token will become the `TELEGRAM_BOT_TOKEN` GitHub Secret.

4. Open your new bot in Telegram and send it one message, for example:

   ```text
   hello
   ```

   Telegram only exposes your chat ID after the bot has received at least one message.

5. Find your Telegram chat ID.

   Open this URL in a browser, replacing `YOUR_TOKEN` with the token from BotFather:

   ```text
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```

   Look for this value in the JSON response:

   ```json
   "chat": {
     "id": 123456789
   }
   ```

   Use that number as `TELEGRAM_CHAT_ID`. In group chats the ID can be negative. If `result` is empty, send another message to the bot and refresh the URL.

6. Edit `config.json` in your fork.

   At minimum, change the placeholder coordinates:

   ```json
   "lat": 46.0,
   "lon": 9.0
   ```

   Set them to your search center. You can also adjust:

   - `radius_km`: search radius in km;
   - `search_hours`: how far ahead to search;
   - `language`: `it`, `en`, `de`, `fr`, or `rm`;
   - `enabled_satellites`: `ISS`, `Tiangong`, `Hubble`, `BlueWalker 3`, `Envisat`.

7. Add the required GitHub Secrets in your fork.

   Go to:

   ```text
   Settings -> Secrets and variables -> Actions -> Repository secrets
   ```

   Add these secrets exactly with these names:

   | Secret | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | The token from BotFather |
   | `TELEGRAM_CHAT_ID` | The chat ID from `getUpdates` |

   Optional: add `USER_LAT` and `USER_LON` as secrets if you want them to override the coordinates in `config.json`.

   Do not put Telegram tokens in `config.json`.

8. Enable GitHub Actions if GitHub asks you to do so.

   Forked repositories sometimes show a banner asking you to enable workflows. Accept it.

9. Allow workflows to write back to the repository.

   Go to:

   ```text
   Settings -> Actions -> General -> Workflow permissions
   ```

   Select:

   ```text
   Read and write permissions
   ```

   Save the setting. This is needed because Telegram commands can update `config.json` and `state/telegram_state.json`.

10. Register the Telegram command menu.

    In GitHub, open:

    ```text
    Actions -> Setup Telegram Commands -> Run workflow
    ```

    Run it once on the `main` branch.

11. Test command processing.

    Send this message to your bot in Telegram:

    ```text
    /help
    ```

    Then in GitHub run:

    ```text
    Actions -> Process Telegram Commands -> Run workflow
    ```

    The bot should reply with the command list.

12. Test the configuration and a manual search.

    Send:

    ```text
    /config
    ```

    Run `Process Telegram Commands` again, or wait for the scheduled workflow.

    Then send:

    ```text
    /run
    ```

    `/run` starts a real transit search and can take longer than simple commands.

13. Leave the scheduled workflows enabled.

    - `Daily ISS Transit Platform` sends the regular daily report.
    - `Process Telegram Commands` checks Telegram periodically and replies to commands.

The detailed setup steps are below.

## Telegram Bot Setup

Open Telegram and search for:

```text
@BotFather
```

Create a new bot:

```text
/newbot
```

Save the generated token. It will be used as the `TELEGRAM_BOT_TOKEN` GitHub Secret.

Then open your new bot in Telegram and send it any message, for example:

```text
hello
```

This step is important: Telegram will not return your chat ID until the bot has received at least one message.

To find your chat ID, open this URL in a browser, replacing `YOUR_TOKEN` with the bot token:

```text
https://api.telegram.org/botYOUR_TOKEN/getUpdates
```

Example:

```text
https://api.telegram.org/bot123456:ABC-DEF/getUpdates
```

Look for:

```json
{
  "ok": true,
  "result": [
    {
      "message": {
        "chat": {
          "id": 123456789
        }
      }
    }
  ]
}
```

Use the `id` value as `TELEGRAM_CHAT_ID`.

Notes:

- For a private one-to-one chat, the ID is usually a positive number.
- For a group chat, the ID is often a negative number.
- If `result` is empty, send another message to the bot and refresh the `getUpdates` URL.
- Keep the bot token private. Do not commit it to `config.json` or any file in the repository.

## Configuration

The main configuration lives in the tracked `config.json` file:

```json
{
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
      "enabled_satellites": ["ISS", "Tiangong", "Hubble", "BlueWalker 3", "Envisat"]
    }
  ]
}
```

Supported `enabled_satellites` values:

- `ISS`
- `Tiangong`
- `Hubble`
- `BlueWalker 3`
- `Envisat`

Supported `language` values:

- `it`
- `en`
- `de`
- `fr`
- `rm`

If `language` is missing or invalid, the bot falls back to Italian.

Current command validation limits:

- `radius_km` must be positive and no more than `500`.
- `search_hours` must be positive and no more than `168`.

The public repository contains safe placeholder coordinates:

```json
"lat": 46.0,
"lon": 9.0
```

After forking, replace them with your own search center.

Important: if your fork is public, coordinates stored in `config.json` are public too. For privacy, make your fork private or use `USER_LAT` and `USER_LON` GitHub Secrets as optional coordinate overrides.

## GitHub Setup

In your fork, go to:

```text
Settings -> Secrets and variables -> Actions
```

Open the `Secrets` tab, then choose `New repository secret`.

Add these required repository secrets exactly with these names:

| Secret | Required | Description |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token from BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Authorized chat ID and default destination chat |

Optional coordinate overrides:

| Secret | Required | Description |
|---|---:|---|
| `USER_LAT` | No | Latitude override |
| `USER_LON` | No | Longitude override |

Do not put Telegram secrets in `config.json`. `config.json` is tracked by Git and may become public if your fork is public.

`TELEGRAM_CHAT_ID` is also the authorization source for Telegram commands. Commands from other chats are rejected and cannot run searches or modify `config.json`.

For Telegram commands that update `config.json` or `state/telegram_state.json`, GitHub Actions must be allowed to push commits back to the repository.

Check:

```text
Settings -> Actions -> General -> Workflow permissions
```

Select:

```text
Read and write permissions
```

Then save the setting.

If GitHub shows a banner asking you to enable workflows in the fork, enable them before running the bot.

### Maintainer-Only Stable Publishing

The private source repository also needs this secret if you maintain the public stable mirror:

| Secret | Required | Description |
|---|---:|---|
| `PUBLIC_REPO_TOKEN` | Only in private source repo | Personal access token used by `publish-stable.yml` to update the public stable repository |

Normal users do not need `PUBLIC_REPO_TOKEN`.

## Telegram Commands

The bot supports these commands:

```text
/start
/help
/status
/config
/run
/setlocation <lat> <lon>
/setradius <km>
/setsatellites <list>
/setsearchhours <hours>
/setlanguage <it|en|de|fr|rm>
```

What they do:

- `/start`: shows a short introduction.
- `/help`: shows the current command list from the command registry.
- `/status`: shows current bot status and main settings.
- `/config`: shows the current configuration.
- `/run`: starts a manual transit search in the same workflow process.
- `/setlocation <lat> <lon>`: updates `config.json` coordinates.
- `/setradius <km>`: updates the search radius.
- `/setsatellites <list>`: updates enabled satellites, for example `iss,tiangong,hubble,bluewalker3,envisat`.
- `/setsearchhours <hours>`: updates the search window.
- `/setlanguage <it|en|de|fr|rm>`: updates the bot language.

Config-changing commands update `config.json`. The command-processing workflow commits and pushes the change back to the repository when the file changed.

If commands do not seem to run automatically, open:

```text
Actions -> Process Telegram Commands
```

Run it manually once and check the logs. Scheduled GitHub Actions can be delayed, especially in low-activity repositories or forks.

## Setup Telegram Command Menu

The Telegram command menu is generated from the real command registry.

After setting `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, run this workflow manually:

```text
Actions -> Setup Telegram Commands -> Run workflow
```

This runs:

```bash
python setup_telegram_commands.py
```

Run it again after publishing new commands or changing command descriptions.

## GitHub Actions Workflows

### Daily ISS Transit Platform

File:

```text
.github/workflows/daily.yml
```

Runs the main transit search:

```bash
python send_telegram.py
```

Triggers:

- manual `workflow_dispatch`
- daily schedule at `01:37 UTC`

The run logs include a compact final summary with run type, status, active satellites, targets, coarse hits, refined hits, final events, close approaches, PNG count, and approximate duration.

### Process Telegram Commands

File:

```text
.github/workflows/process-telegram-commands.yml
```

Checks Telegram updates once, processes new commands, updates `state/telegram_state.json`, and commits config/state changes when needed.

Triggers:

- manual `workflow_dispatch`
- scheduled every 5 minutes

GitHub scheduled workflows can be delayed. A 5-minute cron is not guaranteed to run exactly every 5 minutes.

### Setup Telegram Commands

File:

```text
.github/workflows/setup-telegram-commands.yml
```

Registers the visible Telegram command menu with `setMyCommands`. It is manual only.

### Publish Stable

File:

```text
.github/workflows/publish-stable.yml
```

This workflow is intended for the private source repository only. It is not included in the public stable repository. It publishes a clean copy to:

```text
ericcatta/iss-transit-platform-stable
```

It publishes the files needed by third-party users, including:

- source code;
- translations;
- tests;
- config placeholder;
- Telegram scripts;
- user-facing workflows;
- clean initial Telegram state.

It does not publish `publish-stable.yml` itself, and normal users do not need this workflow.

## Public Stable Repo vs Private Fork

Recommended maintainer/user setup:

- Public stable repository: contains clean code, safe placeholder `config.json`, translations, and user-facing workflows.
- Private fork: contains your personal coordinates, active Telegram secrets, workflow state, and real automation runs.

Users can fork the public stable repository, edit `config.json`, add Telegram secrets, enable workflow write permissions, and run the setup workflow.

If privacy matters, make your fork private before adding real coordinates to `config.json`.

## Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Set required environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your-token"
export TELEGRAM_CHAT_ID="your-chat-id"
```

Optional coordinate overrides:

```bash
export USER_LAT="45.123"
export USER_LON="9.456"
```

Run the main search:

```bash
python send_telegram.py
```

Process Telegram commands once:

```bash
python process_telegram_commands.py
```

Register the Telegram command menu:

```bash
python setup_telegram_commands.py
```

Run the test suite:

```bash
python -m unittest discover -s tests
```

These scripts can send real Telegram messages.

If your system does not provide a `python` command, use `python3` for the local commands above.

## Notes And Limits

- The project currently has no web app or `app/index.html` file.
- The bot depends on live external services: CelesTrak for TLE data and Telegram for delivery.
- GitHub Actions schedules can be delayed or skipped by GitHub under load.
- PNG diagrams are schematic Matplotlib diagrams.
- Report events are ordered predictably: transits first, then close approaches; within each section, events are ordered by time and then by separation.
- The command processor is not a persistent process, webhook, or server. It runs once per workflow execution.
- The project supports one configured user entry at the moment: `users[0]`.
- The public stable repository includes the test suite, so fork users can verify local changes before running the bot.

## Short Roadmap

- Improve README examples as the public stable repository is finalized.
- Add more tests around full end-to-end command flows.
- Improve robustness around very rapid Telegram command sequences.

## License

Personal / amateur astronomy project.
