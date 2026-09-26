# Research Notes

Working notes on approaches considered. Not decisions. See `docs/DECISIONS.md` for what was actually chosen and `docs/LANDSCAPE.md` for a survey of existing tools.

## Constraints that drive everything

- Self-hosted by non-specialists. One process, one database file, one SMTP setting.
- Reliable but not mission critical. Backups are copying a file.
- Not commercial. No pressure toward scale, multi-region, or SLAs.
- Spec is still moving. Cheap to change your mind matters more than cheap to run.

## Data model shape

The natural model is an **append-only event log**. Greensheets, items, and their states are derived from events. This gives:

- The audit log for free. "Everything logged and auditable" is the primary table, not a side effect.
- Trivial show/hide of completed items.
- A tiny schema. One event table plus a few read models.
- A clean answer to the spec's tension between "retains no history" (no conversation history) and "everything logged" (full action history).

Event types identified so far: greensheet created, edited, archived, unarchived, deleted; item created, edited, completed, reopened, deleted; invite sent, accepted, declined; magic link issued, consumed; session revoked; digest sent; person deleted.

## Realtime

"Immediately available to the fulfiller" needs only polling every few seconds or server-sent events. No websockets. Not worth a dependency until something forces it.

## Channels

Decided in D16: channels are typed and extensible. Notes on the shape.

**Link channels** are a URL with the item's context prefilled. The instance holds no credentials and does nothing at click time.

- `mailto:` with subject and body
- `sms:` with body
- `tel:`
- Telegram: `https://t.me/<username>?text=...` opens a chat with prefilled text. Works as a link channel if the requester shares a username.
- WhatsApp: `https://wa.me/<number>?text=...` likewise.

**Bot channels** are needed where no deep link exists. Discord has no prefilled-DM URL; a Discord channel would mean the instance holds a bot token and posts a message, or an invite link, on the fulfiller's behalf. This is the first place the "opens a conversation but never hosts it" line gets tested. Rule: a bot channel sends at most an opening message that identifies the item and the fulfiller. Replies never come back into Greensheet.

**Registry shape.** A channel type has a name, a rendering (link or button), the contact-detail fields it needs, and, for bot channels, an action. Core registers the three link types. Extensions register more. The item stores `[{type, target}]`, not fixed columns.

## API and bridges

Decided in D16. Notes on the shape.

- **API first.** The web interface is a client. On the Django path that means Django Ninja or Django REST Framework serving JSON, with htmx templates calling the same view logic or the API directly. On the Go path, a JSON API with the HTML handlers sharing the service layer.
- **Authentication.** People sign in by magic link and get a session. Programs get an API token issued to a person, scoped to that person's greensheets. Tokens are revocable and logged.
- **Outbound.** Bridges subscribe to the event log. The simplest mechanism is a webhook per greensheet or per person: an HTTP POST per event with a signed payload. Since events are already immutable and ordered, replay and cursoring are cheap to add.
- **Inbound.** Bridges call the same API the page uses: create item, edit item, complete item. A bridge acting for a requester holds that requester's token.
- **Workflow bridges.** A bridge to Asana or similar maps an external task to an item and keeps completion in sync. Greensheet stays the record of expectations toward one person; the workflow tool stays the record of the project. The bridge is the only thing that knows both ids.
- **Where bridges run.** Undecided. In-process plugins are simplest to install; separate processes talking to the API are simplest to write and can't break the core. Likely both, with the API as the contract.

## Authentication comparison

Decided in D1. Comparison retained for reference.

| Mechanism | Multi-device | Recoverable | Operator setup | Fulfiller friction |
|---|---|---|---|---|
| Bare capability link | No | No | None | Zero |
| Email magic link | Yes | Yes | SMTP | Type email, click link |
| Passkeys | Yes if synced | Poor on device loss | None | Confusing first time |
| OAuth (Google, GitHub) | Yes | Yes | Register app per provider | Needs provider account |
| SMS one-time code | Yes | Yes | Paid provider | Low |
| Sheet id plus PIN | Yes | No | None | Remember a PIN |

Magic link is the only row that is multi-device, recoverable, and needs nothing beyond SMTP.

## Stack comparison

| Option | Self-hoster setup | Iteration speed | Notes |
|---|---|---|---|
| Django + SQLite + htmx | One container or venv | Fast | Auth, admin, sessions, migrations, email built in. Admin can be the requester UI and audit viewer on day one. |
| Go + SQLite + html/template + htmx | Copy one binary | Moderate | Assets embedded. Lowest ops burden. Best distribution story. |
| Flask + extensions | One container or venv | Fast at first | Reconstructs most of Django from extensions with less coherence. Sessions are signed cookies by default and not server-revocable. |
| Rails + SQLite + Hotwire | One container | Fast | Excellent fit, heavier runtime. |
| PocketBase + static HTML | One binary | Fast at first | Auth, admin, realtime free. Business rules in JS hooks get awkward. |
| SvelteKit or Next + SQLite | Node runtime, build step | Fast | More moving parts than the problem needs. |

### Why Django over Flask

- **Sessions.** Long-lived, per-device, revocable sessions are core to the auth model. Django stores them in the database; revoking a fulfiller is a delete. Flask's default is a signed cookie.
- **Migrations.** The event schema will change repeatedly during spec phase. Built in versus SQLAlchemy plus Alembic plus wiring.
- **Admin.** A browsable UI over Person, Greensheet, Item, and Event with no code.
- **Coherence.** CSRF, ORM, forms, templates, email, management commands all present and consistent.

Flask wins for a six-route app with no persistence. This app has persistence, auth, sessions, email, and an evolving schema.

**Caveat.** Django's built-in User is password-centric. Use a custom user model from the start with an unusable password and a magic-link auth backend. Well-worn path, small amount of code.

### When to choose Go instead

If the goal becomes "other people self-host this with zero dependencies," a single static binary is a genuinely better distribution story. The app is small enough that slower iteration doesn't hurt much.

### Avoid regardless

- A separate frontend framework and build pipeline.
- A separate database server.
- Realtime infrastructure.
- A job queue. The daily digest is a cron-style management command.
