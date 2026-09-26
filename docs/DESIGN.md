# Design Principles

Why the product looks and behaves the way it does. Read this before designing any surface: page, email, notification, link preview, API response, error message.

## Origin

The name comes from managing an organization where busy people routinely dropped important items. The fix was not a system. It was a sheet of expectations, printed on green paper, handed out routinely. Within weeks the green sheets were recognizable in the noise. People knew what one meant the moment they saw it and spent no time working out the context. They just did what was on it.

That is the whole design brief. Everything below is that experience translated to a browser tab and an inbox.

## The two goals

**Low cognitive burden.** A person encountering a greensheet, on any surface, should know what it is and what to do without reading instructions. The moment of recognition should cost nothing.

**High trust.** A greensheet should feel like a plain piece of paper from someone you know. It never surprises, never nags beyond what was agreed, never hides what happened, and never sells anything.

Every design decision is tested against both. When they conflict, trust wins.

## Principles

### 1. Recognizable in an instant, not noisy

The green sheet worked because it was distinctive without being loud. One consistent visual identity, used the same way on every surface, and nothing else competing with it.

- One mark: a green page, a rectangle with a folded top-right corner in the shape of the universal document icon. It is the favicon, the email sender avatar where supported, the link preview image, and the only decorative element on the page.
- Green is used for identity, never for status. Status uses shape and text.
- No badges, counters, banners, progress bars, or confetti. The item list is the page.

### 2. Uniform and predictable

Familiarity is what made the green paper work. Every greensheet must look like every other greensheet, and every email must look like every other email.

- Fixed grammar for every title and subject line. See Surfaces below.
- Fixed page structure: name, who it is from, items, and nothing above the items.
- One layout for the fulfiller. One layout for the requester. They look the same; the requester's has editing affordances.
- Language from `UBIQUITOUS_LANGUAGE.md` everywhere, including error messages and email bodies. No synonyms.

### 3. One thing to do

The fulfiller's entire interface is the list of items. Each item offers exactly two actions: mark it complete, or reach out through a channel. There is nothing to configure, explore, or learn.

- No navigation chrome on the fulfiller view beyond a link to their other greensheets, if they have any.
- No onboarding tour, no tooltips, no empty-state marketing.
- Settings on the fulfiller side are the digest opt-in and nothing else.

### 4. Nothing hidden

Trust comes from being able to see what happened.

- Every state change shows who did it and when, in the reader's local time.
- The history is a plain chronological list on the same page, one click away, not a separate feature.
- The requester's real name and contact details are visible on the sheet. A greensheet is never anonymous.
- The digest never says anything the page doesn't. It is a summary of the page, not a separate message stream.

### 5. Never more than was agreed

The green sheet was handed out on a routine. It did not follow you around.

- No email that wasn't opted into, except the magic link that was asked for and the single invite.
- The digest is once a day at most, and only if there is something to say.
- No reminder escalation, no "still waiting," no read receipts pushed to the requester.
- Overdue is stated, not shouted. A date in the past, in text. No red.

### 6. Is paper

The word "sheet" invites printing. That is not a metaphor to survive; it is a feature to design for. A greensheet on paper is the original product, and the screen version must produce it seamlessly.

- Printing is first class. Both roles can produce a hard copy from any greensheet in one action, and the browser's own print command produces the same result.
- The hard copy is functional, not decorative: boxes you can tick with a pen, contact details you can dial or type, a way back to the live greensheet.
- A hard copy can be the invite. The requester can hand a printed greensheet to the fulfiller, exactly as in the origin story, and the fulfiller can get from paper to the live greensheet by scanning it.
- Stable URLs. A greensheet's address never changes. A QR code printed today works in a year.
- Plain-text email first. The HTML version, if any, is the plain-text version with the mark at the top.

## Surfaces

### Browser tab

The tab must be findable in a row of thirty.

- Favicon: the green mark. Always. Never a status variant.
- Title grammar: `<greensheet name> · Greensheet`. The name first so it is readable when the tab is narrow; the product last so it is findable by scanning for the suffix.
- No unread counts or dynamic prefixes in the title.

### Email

The subject line must be findable in an inbox of hundreds and must sort predictably.

- Sender name: `Greensheet` on every message. Sender address: one fixed address per instance.
- Subject grammar: `Greensheet: <greensheet name>` followed by a fixed suffix per message type:
  - Invite: `Greensheet: <name> from <requester name>`
  - Magic link: `Greensheet: sign in`
  - Digest: `Greensheet: <name>, <n> new` or `, <n> completed` or `, <n> overdue`, in that order, listing only nonzero counts
- All mail about one greensheet threads together. Use consistent threading headers so inbox clients group them.
- Body: plain text. First line says who the greensheet is from. Second line says what to do. Then the items. Then the link. Nothing else.
- No footers beyond the opt-out line the digest requires. No logos in the body. No tracking.

### Page

- The mark, the name, who it is from, the items. In that order, nothing between.
- Items are the only interactive elements the fulfiller sees, plus channel links within them.
- Completed items are visually quieter, not hidden, unless the requester hides them.
- The requester's editing controls appear inline on hover or focus, not in a toolbar.
- Works at any width. Works without JavaScript for reading and for completing an item.

### Hard copy

The printed greensheet. Designed for Letter and A4, black ink, on whatever paper the reader chooses. Green paper is the reader's decision, so nothing prints with a green background.

Contents, top to bottom:

- The mark, printed solid black with the fold in paper color, small, top left. On green paper this is the original.
- The greensheet name.
- Who it is from: the requester's name and contact details as plain text. Email address and phone number spelled out, since links do not work on paper.
- "As of" date and time, so a stale copy announces itself.
- The items. Each with its item number, an empty box, the title, the note in full, and the due date if any. Completed items print with a filled box and remain listed, unless the reader has hidden them on screen. URLs in notes print as text.
- A QR code and the short URL of the live greensheet, with one line: "Scan to open. Sign in with your email."
- Page number and greensheet name in a running footer when the sheet spans pages. An item never breaks across a page.

Flow:

- A single Print action on the page. It opens the browser's print dialog with the hard copy already laid out. No intermediate settings, no preview page, no "generating."
- The browser's own print command produces the identical result. The hard copy is a print stylesheet on the greensheet page itself, not a separate view.
- Saving as PDF is the browser's print dialog. No server-side PDF at launch; see the candidate in `UBIQUITOUS_LANGUAGE.md`.
- Works for either role and for a reader who is not signed in but has the page open.

Paper and screen stay reconcilable through item numbers. A fulfiller who ticked boxes on paper can find the same items on screen by number. A phone call about "item 4" means the same thing to both people.

### The corner

A greensheet has two faces. The folded corner at the bottom right is how a person turns it over. It reuses the fold from the mark and nothing else in the product uses that motif.

- Fixed at the bottom right of the page, small, quiet. It grows slightly on hover. It shows the green underside of the sheet, which is the other face.
- Clicking turns the sheet over: the page rotates away, the other face rotates in. Under reduced motion it simply navigates.
- For the fulfiller of a front with no flip side, the corner leads to a page that explains what the flip side is and asks before creating anything. Nothing is created by the click alone.
- The corner does not appear on the front for the requester until the flip side exists, and never appears on a hard copy.

### Link preview

When a greensheet URL is pasted into a chat, the preview is the mark and `<name> · Greensheet`. Never the item contents.

### API and bridges

The same principles apply to programs.

- Event names and payload fields use the ubiquitous language verbatim.
- Responses are predictable and small. No envelope cleverness.
- A bridge that posts into Telegram or Discord uses the same subject grammar as email.
- A channel's prefilled message names the greensheet and the item number, so a conversation started from paper and one started from screen read the same.

## Anti-patterns

Things that would make Greensheet unrecognizable or untrustworthy. Do not add them.

- Gamification of any kind: points, streaks, rewards, badges.
- Red overdue styling, urgency language, escalating reminders.
- Rotating or "engaging" subject lines.
- Marketing in transactional email.
- Dashboards, analytics, or summaries above the item list.
- Multiple visual themes or per-requester branding. Every greensheet looks the same; that is the point.
- Any element that changes the mark's color or shape to convey state.

## Relationship to other documents

- Principles 3 and 5 restate spec decisions D5, D6, and D13 as design constraints.
- Principle 6 and the Hard copy surface are decided in D19.
- The item model and channel design are in `docs/DECISIONS.md` D16.
- Vocabulary rules are in `UBIQUITOUS_LANGUAGE.md` and D17.
