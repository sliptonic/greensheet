# Greensheet prototype

A working prototype of the spec in the parent directory. Django, SQLite, htmx, one process.

## Run it

```
cd prototype
uv venv && uv pip install django segno
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed
.venv/bin/python manage.py runserver
```

`seed` creates the tax engagement scenario from `startup.md` and prints a sign-in link for each person. Open one in a browser. Email goes to the console in development, and sign-in links are also shown on screen.

Operator admin is at `/admin`. Create an operator with `manage.py createsuperuser`.

## What is in it

- Magic-link sign-in for everyone. No passwords.
- Home: greensheets for you, greensheets set by you, set a new one. Creating one sends the invite.
- The greensheet page for both roles. Fulfiller completes and reopens. Requester adds, edits, deletes items, edits contact details, archives.
- Channels: Email, Text, Call links per item with the greensheet name and item number prefilled.
- Item numbers, due dates, notes with URLs linked.
- Show or hide completed items.
- History: the event log as a plain list.
- Hard copy: print from the page. Black ink, contact details spelled out, "as of" line, QR code and short URL.
- Daily summary opt-in per greensheet, `manage.py send_digests` to send them.
- Decline link in every invite, which blocks the requester.
- Self-service account deletion with placeholder substitution.
- API tokens at `/me/tokens` and a JSON API under `/api/`. See `sheets/api.py`.
- Operator admin with a read-only event log.

## Not in it yet

- Per-greensheet session revocation.
- Channel types beyond the three link channels; no per-item channel override.
- Outbound webhooks for bridges.
- Operator allowlist for sign-in.
- Rate limiting beyond the daily invite cap.
- Greensheets and items are ordinary rows with an event log written alongside, not derived from events.

## Container

```
docker build -t greensheet prototype
docker run -p 8080:8080 -v greensheet-data:/data -e GREENSHEET_SITE_URL=http://localhost:8080 greensheet
```

Listens on 8080, keeps the database and a generated secret key under `/data`, runs migrations on start, and sends daily summaries from an in-container loop at `GREENSHEET_DIGEST_HOUR`. `GREENSHEET_OPERATOR_EMAIL` grants admin to that address on every start. `GREENSHEET_SEED=1` loads the sample scenario. The GitHub workflow in `.github/workflows/docker.yml` publishes to ghcr.io on `v*` tags.

## Configuration

Environment variables, all optional:

| Variable | Default | Purpose |
|---|---|---|
| `GREENSHEET_SITE_URL` | `http://localhost:8000` | Public URL, used in emails and QR codes |
| `GREENSHEET_DB` | `data/greensheet.sqlite3` | Path to the database file |
| `GREENSHEET_SECRET_KEY` | generated once, kept in the data dir | Set explicitly if you prefer |
| `GREENSHEET_DEBUG` | `1` | Set to `0` in production |
| `GREENSHEET_TZ` | `UTC` | Time zone for dates on screen and paper, and the digest hour |
| `GREENSHEET_DATA` | `data/` | Directory for the database and generated secret key |
| `GREENSHEET_OPERATOR_EMAIL` | unset | Grant admin to this address on start |
| `GREENSHEET_SEED` | unset | `1` loads the sample scenario on start |
| `GREENSHEET_DIGEST_HOUR` | `7` | Local hour for the daily summary; `-1` disables the loop |
| `GREENSHEET_WORKERS` | `2` | Gunicorn workers |
| `GREENSHEET_FROM_EMAIL` | `Greensheet <sheets@localhost>` | The one sender for all mail |
| `GREENSHEET_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_TLS` | unset | Set the host to send real email |
