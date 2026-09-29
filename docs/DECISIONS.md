# Decision Log

Each entry records what was decided, why, and what was rejected. Entries are numbered in the order they were made. Reversing a decision means adding a new entry that supersedes the old one, not editing the old one.

Status values: **Accepted**, **Superseded by Dn**, **Deferred**.

---

## D1. Authentication is by email magic link only

**Status:** Accepted, 2026-09-26

**Decision.** Identity is an email address. A person signs in by requesting a link, which is emailed to them, single use, and short lived. Consuming it establishes a long-lived per-device session. There are no passwords and no registration step. This applies to every role.

**Why.** The original requirement was "minimal startup friction," which pointed to a bare capability link. That fails when either party needs to return from another device or loses the link. Magic links keep the friction at "type your email" while making access recoverable and multi-device. They also make a person a first-class concept, which later enables anyone to be both requester and fulfiller.

**Rejected.**
- *Bare capability link.* Unrecoverable, single device, no identity. Kept only as a possible fallback for fulfillers with no email.
- *Passkeys.* Lowest friction after enrollment, but enrollment confuses non-technical fulfillers and device loss means access loss. Possible later upgrade for requesters.
- *OAuth via Google or GitHub.* Operator must register an app per provider; fulfillers may not have the account.
- *SMS one-time codes.* Requires a paid provider.
- *Sheet id plus PIN.* Weak and adds a secret to lose.

**Cost.** The instance needs outbound email. One SMTP setting at install time.

---

## D2. An instance is open

**Status:** Accepted, 2026-09-26

**Decision.** Anyone with an email address may sign in to an instance and become a requester. The operator may optionally restrict sign-in to an allowlist.

**Why.** The project is not commercial and is meant to be shared with others. An open instance lets a fulfiller turn around and make a greensheet for someone else with no gatekeeping. It is also the only option under which flip side works without an admin step.

**Rejected.**
- *Single operator who is the only requester.* Simplest auth story, but makes the tool personal rather than something others can use.
- *Operator invites requesters.* Adds an admin role and an allowlist as a requirement rather than an option.

**Consequence.** The instance will email addresses typed by strangers. See D3.

---

## D3. Invite abuse is handled by decline, rate limits, and one-email-per-invite

**Status:** Accepted, 2026-09-26

**Decision.** A requester's invite sends exactly one email to the fulfiller's address per greensheet until it is accepted. Every invite email carries a one-click decline that also blocks that requester from inviting that person again. Each requester has a daily invite cap. No other gating.

**Why.** An open instance is a mail source that strangers control. This is the minimum that makes the instance defensible without adding an approval step for legitimate use.

**Rejected.**
- *Fulfiller must accept before seeing content.* Stronger privacy, one more click for every fulfiller. Not worth it for a non-commercial tool.
- *No controls.* Indefensible when discussing with others.

**Open.** Whether a block can be lifted, and by whom.

---

## D4. People arrive by cold sign-in or by invite

**Status:** Accepted, 2026-09-26

**Decision.** A person becomes known to the instance either by visiting the instance URL and entering an email, or by being invited to a greensheet. A person who arrived by invite can create their own greensheets with no further step.

**Why.** Follows from D2. Any distinction between "invited person" and "signed-up person" would be an artificial gate.

**Rejected.**
- *Invite-only with operator seeding.* Limits abuse but makes the operator a bottleneck.
- *Fulfillers stay fulfillers.* Cleaner roles, but makes flip side awkward and adds a sign-up concept.

---

## D5. Notifications are a per-greensheet opt-in daily digest

**Status:** Accepted, 2026-09-26

**Decision.** The greensheet page always shows current state. Each party may opt in, per greensheet, to one email per day summarizing changes: items added for the fulfiller, items completed for the requester, overdue items for both. Greensheet sends no other email about changes.

**Why.** Requesters will want to know when things get done, and fulfillers will want to know when things are added. Per-event email makes Greensheet a noisy mail source and blurs the line with being a communication channel. A digest gives the information without the noise.

**Rejected.**
- *Immediate email on every change.* Noisy.
- *No notifications.* Strictly consistent with "not a communication channel," but requesters will ask for it immediately.

**Needs validation.** Including overdue items in the digest was an assistant addition, not an explicit choice.

---

## D6. An item is a title, optional note, optional channels, optional due date

**Status:** Accepted, 2026-09-26

**Decision.** An item has a one-line title, an optional plain-text note with URLs presented as links, optional channels, and an optional due date. Due dates are informational: displayed on the sheet and in digests, no escalation. No attachments.

**Why.** Expectations usually have a "by when." A note gives room for context without cramming it into the title. Attachments would make Greensheet a file host with storage, limits, and retention concerns. Anything the fulfiller must receive travels through a channel or a URL.

**Rejected.**
- *Title and channels only.* Requesters would stuff context into titles.
- *Attachments.* Out of scope.
- *No dates.* Requesters would put dates in the title text.
- *Overdue emphasis on the page.* Adds pressure on the fulfiller. Not chosen, though see D5.

---

## D7. Subtasks are out for now

**Status:** Deferred, 2026-09-26

**Decision.** Items do not nest. Revisit later.

**Why.** Nesting is the first step toward dependencies, which the spec rejects. An expectation with sub-steps can be several items. Left open rather than closed permanently.

---

## D8. Flip side is adopted as a concept; the feature is deferred

**Status:** Superseded by D20, 2026-09-26

**Decision.** A flip side is a greensheet with the roles of an existing greensheet reversed, paired with it. The pairing feature is not scheduled. Since any person can be a requester (D2, D4), a fulfiller can already create the unpaired equivalent.

**Why.** Naming it keeps the vocabulary ready and prevents designing it out. Building it now adds nothing that a second greensheet doesn't already give.

---

## D9. Archive is read-only and visible to both parties

**Status:** Accepted, 2026-09-26

**Decision.** Archiving makes a greensheet read-only for both parties. It stays visible to both. The requester may unarchive.

**Why.** Preserves the fulfiller's record of what they did and the full audit trail. Revoking the fulfiller's access on archive would make the history one-sided.

**Rejected.**
- *Hidden from fulfiller.* Asymmetric.
- *Delete with grace period.* Loses history.

---

## D10. A greensheet's requester and fulfiller never change

**Status:** Accepted, 2026-09-26

**Decision.** Both roles are bound for the lifetime of the greensheet. To change the fulfiller, archive the sheet and create a new one. Copying items to a new sheet may be added as a convenience later.

**Why.** Keeps "exactly one fulfiller" literally true and the audit log unambiguous. Reassignment would mix two people's completion history on one sheet.

**Rejected.**
- *Requester can reassign.* Handles typos in the invite address, at the cost of ambiguous history.

---

## D11. Contact details live on the greensheet

**Status:** Accepted, 2026-09-26

**Decision.** Each greensheet carries the requester's contact details for that relationship: email, defaulting to the sign-in address, and optional phone. Items inherit them for their channels and may override. Channels are mailto, sms, and tel.

**Why.** A contractor may not want the same number on every sheet, but typing contact details on every item is tedious. Per-sheet with per-item override is the middle.

**Rejected.**
- *Per-item only.* Tedious, error-prone.
- *Per-person profile.* Same details on every sheet.

---

## D12. Self-service account deletion

**Status:** Accepted, 2026-09-26

**Decision.** A person can delete themselves. Greensheets they own are deleted. Greensheets where they are the fulfiller survive for the requester with the person replaced by a placeholder. Audit events remain.

**Why.** An open instance stores strangers' email addresses. They need an exit that doesn't require finding the operator.

**Rejected.**
- *Operator-only deletion.* Weak for an open instance.
- *No deletion.* Deferred entirely; not acceptable given D2.

---

## D13. Both parties see the full audit log of their greensheet

**Status:** Accepted, 2026-09-26

**Decision.** Every event on a greensheet is visible to its requester and its fulfiller as a plain chronological list. The operator sees everything.

**Why.** Transparency is part of clarifying expectations. A one-sided history undermines trust.

**Rejected.**
- *Requester only.* Asymmetric.
- *Operator only.* Wastes the "everything logged" requirement as a product feature.

---

## D14. License is undecided; project is private

**Status:** Deferred, 2026-09-26

**Decision.** No license yet. The README stays silent on it.

**Options when revisited.** Permissive (MIT) fits non-commercial self-hosted and lets collaborators fork freely. Copyleft (AGPL) prevents closed commercial forks.

---

## D15. Technology stack: Django, SQLite, htmx

**Status:** Accepted, 2026-09-26

**Decision.** Django, SQLite, and htmx, shipped as one container. Decided with the 0.1.0 release; the prototype below became the application in `app/`. Earlier text kept for the record: not formally decided. See `docs/RESEARCH.md` for the comparison. Current leaning is a server-rendered app with an embedded database and minimal client script, shipped as one container or binary. D16 adds a constraint: whatever is chosen must expose an HTTP API that the web interface itself uses.

**Prototype (2026-09-26).** Built on Django 6, SQLite, and htmx in `prototype/`. It implements D1 through D14, D16 in part (link channels and a JSON API with tokens; no bridges or webhooks yet), D17, D18, and D19. Its README lists what is missing. This is not yet a stack decision; it is evidence for one.

---

## D16. Channels and bridges are extension points behind an API

**Status:** Accepted, 2026-09-26

**Decision.** The design anticipates expansion in two directions, and treats both as extensions rather than core.

- **Channels** are typed. The core ships link channels: email, SMS, phone. New channel types, such as Telegram or Discord, register with the instance and know how to render or initiate a conversation for an item. A channel type that requires the instance to send a message on the fulfiller's behalf is a bot channel; it still only opens a conversation elsewhere.
- **Bridges** connect an instance to external systems, including workflow tools. They are built on two things the core already has: an HTTP API through which every web action is also available, and the event log, which bridges can subscribe to. A bridge may create or update items from outside or push events out.
- The web interface is a client of the API. Nothing is reachable from the page that isn't reachable from the API.
- Programs authenticate with API tokens issued to a person. Tokens are not a sign-in mechanism for people; D1 stands.

**Why.** Channels are the feature that distinguishes Greensheet from every tool in `docs/LANDSCAPE.md`, and the survey shows that asymmetric tools grow feedback loops under pressure. Making channels a first-class, extensible concept gives that pressure somewhere to go that isn't "add comments." Bridges answer the open question about fitting in with tools like Asana without making Greensheet a workflow system: it stays the record of expectations and hands off everything else. Deciding API-first now costs little and avoids a rewrite when the first bridge is wanted.

**Rejected.**
- *Hard-code mailto, sms, tel.* Cheapest today, but the first messaging-app request forces a refactor of the item model.
- *Comments or threads on items.* The obvious feedback loop; explicitly rejected by the spec. Channels are the alternative.
- *Export only.* Insufficient for a live bridge.

**Consequences.**
- The item model carries a list of channels, each with a type and target, rather than three fixed fields.
- The event log needs a stable, documented shape, since bridges depend on it.
- The stack decision (D15) must produce a clean API. Django REST Framework or Django Ninja on the Django path; standard library on the Go path.
- Bot channels imply the instance holds credentials for external services. Kept out of core, configured per extension.

**Open.** Which bridges and channel types to build first. Whether bridges are in-process plugins, separate processes talking to the API, or both.

---

## D17. Avoid "checklist", "to-do", and "task list" vocabulary

**Status:** Accepted, 2026-09-26

**Decision.** These words are not used for a greensheet in product copy or project documents, except when naming what Greensheet is not. Use "greensheet", "item", and "expectation".

**Why.** `docs/LANDSCAPE.md` found that every tool described with those words is symmetric: the person holding the list can add to it. The words carry that assumption. Greensheet's defining property is that the fulfiller cannot add. The coined noun does work that "checklist" would undo.

---

## D18. Recognizable, uniform, quiet: low cognitive burden and high trust

**Status:** Accepted, 2026-09-26

**Decision.** The product's origin, a sheet of expectations printed on green paper that became instantly recognizable in a busy organization, is the design brief. Every surface is designed for two goals: low cognitive burden and high trust. When they conflict, trust wins. The principles and their concrete implications per surface are in `docs/DESIGN.md`.

The headline constraints:

- One visual mark, a green page icon with a folded corner, used identically on every surface and never varied to show state. Green is identity, not status.
- Fixed grammar for browser titles and email subjects, so a greensheet is findable among thirty tabs or hundreds of messages by shape alone.
- All mail about one greensheet threads together. Plain text first.
- The fulfiller's interface is the item list and nothing else. Each item offers two actions.
- Nothing hidden: who did what and when is always visible.
- Never more than was agreed: no unrequested email, no escalation, no red.
- Feels like paper: prints well, stable URLs, looks the same every time.

**Why.** The green paper worked because recognition cost nothing and it never surprised anyone. Those are properties of consistency and restraint, and they are easy to lose one feature at a time. Writing them down as a decision makes each future "just add a badge" a decision to reverse this one.

**Rejected.**
- *Per-requester branding or themes.* Would let each greensheet look different, which defeats recognizability.
- *Status-colored favicon or dynamic tab titles.* Findable, but noisy, and makes the mark unreliable.
- *Engaging notification copy.* Trades predictability for attention.
- *Gamification.* The chore-app market is built on it; see `docs/LANDSCAPE.md`. It is the opposite of a plain sheet of paper.

**Consequences.**
- Printing is first class; see D19.
- The email subject grammar and title grammar are specified in `docs/DESIGN.md` and are part of the spec, not a styling detail.
- Bridges that post into chat systems use the same grammar.

---

## D19. Printing is a first-class feature

**Status:** Accepted, 2026-09-26

**Decision.** A hard copy of a greensheet is a primary output, not a stylesheet afterthought. Either role produces one in a single action from the greensheet page, and the browser's own print command yields the same result. The hard copy is functional on paper: item numbers, boxes to tick, the requester's contact details spelled out, an "as of" timestamp, and a QR code with a short URL back to the live greensheet. A hard copy may serve as the fulfiller's invite.

To make paper and screen refer to the same thing, every item gets a stable **item number** at creation, unique within its greensheet and never reused. Item numbers appear on screen, on paper, and in channel messages.

Full specification of the hard copy is in `docs/DESIGN.md` under Surfaces.

**Why.** The product is named after a piece of paper. "Sheet" invites printing, and the origin story is a printed sheet handed to a person. A fulfiller who prefers paper should get an experience as good as the screen, and the requester should be able to reproduce the original ritual: hand someone a green sheet. Designing for this after the fact produces ugly printouts with broken links and no way back.

**Rejected.**
- *Print stylesheet only, no item numbers, no QR.* Produces paper that cannot be reconciled with the screen or lead back to it.
- *Separate print view or server-generated PDF at launch.* Adds a step and a moving part. The browser's print pipeline is sufficient and universal. Server-side PDF remains a candidate for bridges and email.
- *Green background in print.* Wastes ink, looks wrong on white, and is redundant on green paper. The reader chooses the paper.

**Consequences.**
- Item number joins the item model and the ubiquitous language.
- Channel messages name the greensheet and item number, so conversations started from paper and screen read the same.
- Stable short URLs and QR generation are launch requirements.
- Reading and completing must work without JavaScript, since the printed URL may be opened on anything.
- The "as of" timestamp means a hard copy is honest about being a snapshot; there is no attempt to sync paper back automatically.

---

## D20. The flip side is a feature, created by the fulfiller from a folded corner

**Status:** Accepted, 2026-09-26. Supersedes D8.

**Decision.** A greensheet has two faces. The front is what the requester needs from the fulfiller. The flip side is what the fulfiller needs from the requester: a second greensheet with the same two people and the roles reversed, paired with the front for life.

- The fulfiller creates it. On the front, a folded corner sits at the bottom right of the page. Clicking it turns the sheet over to a page that explains the flip side and asks whether to create it. Confirming creates it and lands on it, ready for items.
- Once it exists, both faces show the corner, and it turns the sheet over to the other face. The turn is animated, and skipped when the viewer prefers reduced motion.
- The flip side is named "Flip side of <name>" and can be renamed. Its contact details start as the new requester's sign-in email; phone is blank until set.
- No invite email. The other party is already here. They see it on their home page, on the front's corner, and in their daily summary if opted in. An accepted invite record is created for consistency.
- The requester of the front cannot create the flip side; there is no corner for them until it exists. A flip side has no flip side of its own.
- Everything else is an ordinary greensheet: items, channels, history, hard copy, archive, digest. Archiving one face does not archive the other.

**Why.** The fulfiller often needs things from the requester too. The contractor needs the client's documents; the client needs the contractor's schedule and invoice. Making the fulfiller create a separate unrelated greensheet loses the pairing and the moment of discovery. The folded corner reuses the one visual motif the product has, the fold on the mark, and turning the sheet over is exactly what you would do with paper.

**Rejected.**
- *Requester creates it on the fulfiller's behalf.* Inverts who is asking.
- *Both faces in one page, tabs or columns.* Breaks "one thing to do" and makes the hard copy ambiguous.
- *Automatic creation.* An empty flip side for every greensheet is noise.
- *Notify the requester by email when the flip side is created.* Not agreed to; the digest covers it for those who opted in.

**Consequences.**
- The item numbers on each face are independent. "Item 3" is ambiguous without saying which face; channel messages and digests name the face by its greensheet name, which carries "Flip side of".
- The corner is the second and last use of the fold motif. It is not to be reused for other actions.
- Print omits the corner.

---

## D21. Text and Call are mobile only; desktop email is a remembered choice

**Status:** Accepted, 2026-09-27

**Decision.** On a phone, the Email, Text, and Call channels stay as plain `mailto:`, `sms:`, and `tel:` links. On a desktop, Text and Call are not offered, because a desktop has no reliable handler for them. Email on a desktop opens, on first use, a small choice of how to compose: the default mail app, Gmail, Outlook.com, Microsoft 365, or copy the address and message. The choice is remembered in the browser and shown as "via Gmail" next to the link, where it can be changed. Device detection is client-side and a wrong guess only changes which links appear.

**Why.** `sms:` and `tel:` do nothing on most desktops, and `mailto:` opens whatever the OS thinks the mail client is, which for web mail users is often wrong or unset. Web mail compose URLs fix email for most people. Nothing fixes SMS from a desktop without a paid gateway, which D1 already declined.

**Rejected.**
- *Copy only.* Works but is a chore. Kept as one of the choices.
- *QR handoff to the phone.* Clever, still an extra step; may come back.
- *Instance sends the message on the fulfiller's behalf.* The bot channel from D16. Reliable everywhere and stays within the one-opening-message rule, but adds a message form to the page. Deferred, not rejected.

---

## D22. The invite links to the greensheet, not to a sign-in link

**Status:** Accepted, 2026-09-28

**Decision.** The invite email carries the greensheet's stable address, `<site>/s/<code>`. Opening that address signed out shows a form asking for the email address the greensheet was sent to; submitting it sends a magic link that returns to the same greensheet. Magic links are sent only when someone asks for one, from that form or from the plain sign-in page. An expired or used link points back to the page it was going to.

**Why.** The invite used to embed a magic link, which expires in fifteen minutes and works once. Fulfillers do not open invites within fifteen minutes, and an expired invite is a dead end that makes the product look broken. With the greensheet's address in the invite, the email is a permanent way back: keep it, open it from any device, sign in if asked. This is the same address that the hard copy's QR code and the digest already carry, so every route to a greensheet is now the one route.

**Rejected.**
- *Longer-lived invite links.* A link that signs you in for weeks is a credential sitting in an inbox, and it still dies eventually.
- *Sending the sign-in link without asking for the email.* The page would have to guess who is visiting from a guessable code, and anyone with the address could flood a party's inbox and use up their rate limit.
- *Both addresses in the invite.* Two links to explain, and the first one still expires.

**Consequences.**
- The invite no longer counts against the fulfiller's magic-link rate limit.
- Invite acceptance is recorded on the fulfiller's first sign-in, as before.
- The sign-in form on a greensheet reveals nothing about the greensheet; it looks the same for any code.

---

## D23. A greensheet may carry one glyph on its mark

**Status:** Accepted, 2026-09-29

**Decision.** The requester may set an icon for a greensheet: one character or emoji, drawn in paper colour on the green mark. It appears on the browser tab, beside the name on the sheet, and on the row on the desk. The flip side inherits it. Nothing else about the mark changes: the shape, the fold, and the green are fixed, and the glyph never signals status.

**Why.** The rule that the favicon is always the plain mark made every greensheet tab identical, which defeats the purpose of a findable tab once someone has several open. A glyph the requester chose is the smallest change that makes tabs tell apart, and it keeps the mark recognisable as Greensheet.

**Rejected.**
- *A colour per greensheet.* Green is identity. A palette would make some greensheets look less like Greensheet, and colour reads as status.
- *Uploaded images.* Storage, moderation, and a mark that no longer looks like the mark.
- *Auto-generated glyphs from the name.* Two greensheets with similar names get similar glyphs, and nobody chose them.

**Consequences.**
- The icon is one field, at most sixteen code points so a joined emoji fits, cleaned but never rejected.
- Pages that are not about one greensheet keep the plain mark.
