# About

Greensheet is a tool for setting, managing, and clarifying expectations.

The name comes from managing an organization where busy people routinely dropped important items. The fix was a sheet of expectations printed on green paper and handed out routinely. Within weeks the green sheets were recognizable in the noise: people knew what one meant instantly and spent no time working out the context. Greensheet is that experience translated to a browser tab and an inbox. The design goals are low cognitive burden and high trust. See `docs/DESIGN.md`.

## Project Status

This is a greenfield project. It is unrelated to any other projects or sessions. The spec is drafted and a working prototype exists in `prototype/`. There are no users, contracts, or external constraints.

It is not intended to be a commercial product at this time. It is intended to be simple to self-host: reliable, but not mission critical. Licensing is undecided; the project is private for now.

## AI Guidance

- `README.md` at the project root keeps a short but accurate description of the project. It is meant to be end-user readable and capture the essential ideas.
- `UBIQUITOUS_LANGUAGE.md` at the project root keeps formal definitions and shared vernacular. Consult it before making any design recommendations. Keep it up to date and accurate. Prompt the user to validate content changes.
- `docs/DECISIONS.md` is the decision log. Every design decision gets a numbered entry with rationale and rejected alternatives. Reversing a decision means a new entry that supersedes the old one.
- `docs/RESEARCH.md` holds working notes and comparisons that inform decisions but are not decisions.
- `docs/LANDSCAPE.md` surveys existing tools against the two defining requirements: low friction and asymmetry of action.
- `docs/DESIGN.md` holds the design principles derived from the origin story: recognizable, uniform, one thing to do, nothing hidden, never more than agreed, feels like paper. Consult it before designing any surface.
- Additional research and planning documents may be created under `docs/` as needed. This file may be edited as needed.
- `prototype/` is a working Django implementation of the spec. Its `README.md` says how to run it and what it does not yet do. Keep it consistent with the decisions; when the prototype and a decision disagree, the decision wins or gets a superseding entry.

## Brief Description

### What it is

A **greensheet** is a set of expectations one person sets for a second person. For example, a parent might set out chores they expect a child to perform. A contractor might set out the actions they need a client to take before work can commence.

Items are placed on the greensheet by the first person, the **requester**, and marked done by the second person, the **fulfiller**.

Each item may carry one or more **channels**: mechanisms for the fulfiller to initiate communication about that item through an external application. Email, SMS, and phone come first; messaging apps such as Telegram and Discord are anticipated.

Example:

```
- [ ] Contact IRS regarding early payment options  (email)  (SMS)
```

A greensheet may persist for a long time, with new items added over time and other items marked done.

### What it is not

- **Not a shared task list.** Each greensheet has exactly one fulfiller, who is a single human being, and exactly one requester, who is also a single human being.
- **Not a communication channel.** Discussion _about_ items happens through external channels. Greensheet may open a conversation elsewhere but never hosts one. It retains no message history internally. It does retain a full action history.
- **Not a workflow management system.** There are no dependencies between items. Greensheet may bridge to a workflow system, but is not one.
- **Not a to-do list or checklist.** Those words imply the person holding the list can add to it. Avoid them in product copy and in these documents except when naming what Greensheet is not.

## Typical Scenario

A contractor meets a new client and agrees to take on a job. They discuss the details and the contractor notes what will be required to proceed. At the end of the meeting, the contractor says, "I'll send you a greensheet later today and start as soon as I have what I need."

Later that day, the contractor (requester) creates a new greensheet and adds the items:

```
- [ ] Sign the engagement letter sent to you by email  (email)  (SMS)
- [ ] Provide 2024 and 2025 tax returns and supporting documentation  (email)  (SMS)
- [ ] Send contact information for bookkeeper  (email)  (SMS)
- [ ] Send contact information for attorney  (email)  (SMS)
```

The requester invites the client (fulfiller) by email. The fulfiller receives a link, opens the greensheet in a browser, and reviews the items. For each item, the fulfiller has only two options:

- Mark the item as complete.
- Initiate a communication through one of the item's channels, such as email or SMS.

The requester can show or hide completed items.

After some time, the requester thinks of another item and adds it to the greensheet. The item becomes immediately available to the fulfiller. If the fulfiller has opted in, it also appears in their next daily digest email.

## Decisions

Design decisions, with rationale and rejected alternatives, are recorded in `docs/DECISIONS.md`. Research and comparisons are in `docs/RESEARCH.md`. The short form of every decision is reflected in `README.md` and `UBIQUITOUS_LANGUAGE.md`.

## Technology Stack

### Requirements

- Browser based for both requester and fulfiller. No local app installation.
- Low startup friction. Very low is ideal, but both requester and fulfiller may need to return to a greensheet later or from another device, so a low-friction authentication or token mechanism is acceptable over a bare shared link.
- Reasonable security.
- Everything logged and auditable.
- Recognizable in an instant on every surface: browser tab, inbox, link preview. Uniform and predictable. Not noisy.
- Printing is first class. A hard copy is produced in one action, is functional on paper, and leads back to the live greensheet.
- Simple to self-host: one process, one database file, outbound email via SMTP.
- API first. Every action available in the web interface is available through an HTTP API. Channels and bridges are extension points, not core code.

### Direction

Not formally decided. The prototype in `prototype/` is Django, SQLite, and htmx, per the leaning recorded in D15. See `docs/RESEARCH.md` for the comparison.

## Roles

- **Requester**: creates and manages a greensheet and its items, invites the fulfiller, sets contact details.
- **Fulfiller**: views a greensheet, marks items complete or reopens them, initiates communication through channels.
- **Operator**: runs the instance. Has no role on any greensheet by default.

## User Stories

### Any person

- Sign in from any device with an email address.
- Decline an invite and block the sender.
- Opt in or out of the daily digest per greensheet.
- View the full history of a greensheet they are party to.
- Print a hard copy of a greensheet they are party to.
- Delete their account.

### Requester

- Manage a greensheet: create, read, update, archive, unarchive, delete.
- Set contact details for a greensheet.
- Invite a fulfiller to a greensheet, by email or by handing them a hard copy.
- Revoke the fulfiller's sessions on a greensheet.
- Manage an item on a greensheet: create, read, update, delete.
- Show or hide completed items.

### Fulfiller

- View a greensheet.
- Mark an item complete, or reopen it.
- Initiate communication about an item through a channel.

### Operator

- Install and run an instance with an SMTP configuration.
- Optionally restrict sign-in to an allowlist.
- View all data and the full audit log.

## Open Questions

- Subtasks. Deferred, D7.
- Which bridges to build first. The bridge mechanism is decided in D16; specific targets are not.
- License. Deferred, D14.
- Technology stack. Deferred, D15.
- Can a decline block be lifted, and by whom? Raised in D3.
