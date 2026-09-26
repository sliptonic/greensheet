# Greensheet application

Django, SQLite, htmx, one process. This implements the spec in the parent directory. See `docs/DECISIONS.md` for what was decided and why.

## Run it locally

```
cd app
uv venv && uv pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed
.venv/bin/python manage.py runserver
```

`seed` creates the tax engagement scenario from `startup.md` and prints a sign-in link for each person. Email goes to the console in development, and sign-in links are also shown on screen.

Tests:

```
.venv/bin/python manage.py test
```

## What is in it

- Magic-link sign-in for everyone. No passwords. Links are single use, expire in 15 minutes, and are rate limited.
- Home: greensheets for you, greensheets set by you, set a new one. Creating one sends the invite.
- The greensheet page for both roles. Fulfiller completes and reopens. Requester adds, edits, deletes items, edits contact details, archives.
- The flip side. The fulfiller turns the greensheet over with the folded corner at bottom right and sets out what they need from the requester. Same two people, roles reversed, paired for life. Both faces show the corner once it exists.
- Channels: Email, Text, Call links per item with the greensheet name and item number prefilled.
- Item numbers that never reuse, due dates, notes with URLs linked, show or hide completed.
- History: the event log as a plain list, per greensheet.
- Hard copy: print from the page. Black ink, contact details spelled out, "as of" line, QR code and short URL.
- Daily summary opt-in per greensheet. Sent by an in-container loop or `manage.py send_digests`.
- Decline link in every invite, which blocks the requester. Daily invite cap.
- Sign the other party out everywhere, from the greensheet's edit page.
- Optional operator allowlist for cold sign-in. Invited people always get in.
- Self-service account deletion with placeholder substitution.
- API tokens at `/me/tokens` and a JSON API under `/api/`. See `sheets/api.py`.
- Webhooks at `/me/webhooks`: every event on your greensheets, POSTed as JSON and signed. See `sheets/webhooks.py`.
- Operator admin with a read-only event log.

## Not in it

- Channel types beyond the three link channels; no per-item channel override.
- Inbound bridges beyond the JSON API.
- Webhook retries.
- Greensheets and items are ordinary rows with an event log written alongside, not derived from events.

## Container

```
docker build -t greensheet app
docker run -p 8080:8080 -v greensheet-data:/data -e GREENSHEET_SITE_URL=http://localhost:8080 greensheet
```

Listens on 8080, keeps the database and a generated secret key under `/data`, runs migrations on start, and sends daily summaries from an in-container loop at `GREENSHEET_DIGEST_HOUR`. `GREENSHEET_OPERATOR_EMAIL` grants admin to that address on every start. `GREENSHEET_SEED=1` loads the sample scenario. The GitHub workflow in `.github/workflows/docker.yml` publishes to ghcr.io on `v*` tags.

## Configuration

Environment variables, all optional:

| Variable | Default | Purpose |
|---|---|---|
| `GREENSHEET_SITE_URL` | `http://localhost:8000` | Public URL, used in emails and QR codes |
| `GREENSHEET_DB` | `data/greensheet.sqlite3` | Path to the database file |
| `GREENSHEET_DATA` | `data/` | Directory for the database and generated secret key |
| `GREENSHEET_SECRET_KEY` | generated once, kept in the data dir | Set explicitly if you prefer |
| `GREENSHEET_DEBUG` | `1` | Set to `0` in production. The container does. |
| `GREENSHEET_TZ` | `UTC` | Time zone for dates on screen and paper, and the digest hour |
| `GREENSHEET_ALLOWLIST` | unset | Comma-separated emails or domains allowed to sign in cold |
| `GREENSHEET_OPERATOR_EMAIL` | unset | Grant admin to this address on start |
| `GREENSHEET_SEED` | unset | `1` loads the sample scenario on start |
| `GREENSHEET_DIGEST_HOUR` | `7` | Local hour for the daily summary; `-1` disables the loop |
| `GREENSHEET_WEBHOOKS` | `1` | `0` disables outbound webhooks |
| `GREENSHEET_WORKERS` | `2` | Gunicorn workers |
| `GREENSHEET_FROM_EMAIL` | `Greensheet <sheets@localhost>` | The one sender for all mail |
| `GREENSHEET_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_TLS` | unset | Set the host to send real email |
