# Ubiquitous Language

Formal definitions and shared vernacular for the Greensheet project. Consult this file before making design recommendations. Changes to this file should be validated by the project owner.

## Terms

### Instance

One running deployment of Greensheet, operated by an **operator**. An instance is **open**: any person with an email address may sign in and become a requester. The operator may restrict sign-in to an allowlist.

### Operator

The person who runs an instance. The operator has no role on any greensheet by default but can see all data and the full audit log.

### Greensheet

A set of expected actions a **requester** sets for a single **fulfiller**. A greensheet contains zero or more **items** and carries the requester's **contact details** for that relationship. It may persist indefinitely, with items added and completed over time. A greensheet can be **archived**. A greensheet may carry an **icon**, one character or emoji the requester chose, drawn on the mark so its tab and its row stand out. A new greensheet may **start from** one the requester created before: its items are copied, with due dates counted from today; nothing else carries over.

A greensheet has exactly one requester and exactly one fulfiller, bound for its lifetime. Neither can be changed.

Also the name of the product as a whole. Where ambiguity matters, "a greensheet" refers to one set of expectations and "Greensheet" refers to the product.

The name refers to a sheet of expectations printed on green paper, which became instantly recognizable in a busy organization. The word "sheet" is deliberate and carries the paper metaphor: a greensheet is handed to you, it looks the same every time, and it can be printed.

### Hard copy

A printed rendering of a greensheet, produced by the reader in one action from the greensheet page or by the browser's print command. A hard copy is a snapshot: it states when it was made. It carries the mark, the name, the requester's contact details in plain text, every item with its item number and a box, and a QR code and short URL back to the live greensheet. A hard copy can serve as the invite: the requester may hand one to the fulfiller.

### Mark

The single visual identifier of Greensheet: a green page, a rectangle with a folded top-right corner in the familiar shape of a document icon. It appears as the favicon, in link previews, and once on each page. It never changes color or shape to convey state. Green is used for identity only, never for status.

### Item

A single expected action on a greensheet. An item has a **title**, an optional **note**, optional **channels**, and an optional **due date**. An item is created by the requester and is either **open** or **complete**. Items have no dependencies on one another and no ordering semantics beyond display.

### Item number

A small integer assigned to an item when it is created, unique within its greensheet and never reused. It is a label, not an ordering: items may be displayed in any order, and deleting an item leaves a gap. Item numbers appear on screen, on hard copies, and in channel messages so that paper, screen, and conversation refer to the same item.

### Title

The one-line text of an item.

### Note

Optional longer plain text on an item. URLs in a note are presented as links. Notes cannot contain attachments.

### Due date

An optional date on an item indicating when the requester expects it complete. Informational only: shown on the greensheet and in digests. An item past its due date and still open is **overdue**. There is no escalation.

### Contact details

The email address and optional phone number a requester provides on a greensheet so the fulfiller can reach them about its items. Email defaults to the requester's sign-in address. Items inherit contact details for their channels and may override them.

### Channel

A mechanism on an item by which the fulfiller initiates communication about that item through an external application. Every channel has a **channel type** and a target drawn from contact details. Greensheet may open the conversation but never hosts it, and retains no message history.

### Channel type

A kind of channel, registered with the instance. The core types are **link channels**: email (mailto), SMS (sms), and phone (tel), each rendered as a link that opens the external application with the item's context prefilled. Additional types, such as Telegram or Discord, may be added as extensions. A channel type that requires the instance to send a message on the fulfiller's behalf is a **bot channel**; it still only opens a conversation elsewhere.

### Bridge

A connection between an instance and an external system, built on the **API** and the event log. A bridge may create or update items from outside, or notify an external system when events occur. Bridges are extensions, not core. Greensheet remains the record of expectations; the bridged system remains the record of whatever it tracks.

### API

The HTTP interface through which everything the web interface can do can also be done by a program. The web interface is a client of the API. Programs authenticate with an **API token** issued to a person; tokens are not a sign-in mechanism for people.

### Person

A human being known to the instance, identified by an email address. A person holds a **role** on each greensheet they are associated with. The same person may be the requester on one greensheet and the fulfiller on another. There are no passwords; a person proves identity through a **magic link**. A person may delete themselves.

### Requester

The role held by the person who creates and owns a greensheet. The requester creates, edits, and deletes items, sets contact details, invites the fulfiller, can revoke the fulfiller's sessions, and can archive or unarchive the greensheet. Each greensheet has exactly one requester.

### Fulfiller

The role held by the person expected to perform the actions on a greensheet. Each greensheet has exactly one fulfiller, who is always a single human being. The fulfiller can view the greensheet and its history, mark items complete or reopen them, and initiate communication through channels. The fulfiller cannot add, edit, or delete items. A fulfiller may also be a requester on other greensheets.

### Invite

The act by which a requester associates a person, by email address, with a greensheet as its fulfiller. An invite sends the fulfiller one email containing the greensheet's address. Opening that address signed out asks for an email and sends a magic link that returns to the greensheet. No further invite email is sent for that greensheet and address until the invite is accepted. Every invite email carries a **decline** link. Requesters have a daily invite cap.

### Decline

The act by which an invited person refuses an invite. Declining blocks the inviting requester from inviting that person again.

### Magic link

A single-use, short-lived URL emailed to a person that proves they control that email address. Consuming a magic link establishes a **session**. Magic links are the only authentication mechanism for all roles.

### Session

A long-lived association between a person and a browser on one device, established by consuming a magic link. A person may hold sessions on several devices at once. A requester can revoke the fulfiller's sessions on a greensheet.

### Open

The state of an item that has not been marked complete.

### Complete

The state of an item that has been marked done. Completed items remain on the greensheet but are hidden from the list by default; either party may show or hide them, and the choice is remembered per device. Either role may **reopen** a completed item; doing so is logged.

### Archive

An action the requester takes on a greensheet that is no longer active. An archived greensheet is read-only for both parties and remains visible to both. The requester may unarchive it.

### Digest

An optional daily email, opted into per greensheet by each party independently, summarizing changes on that greensheet since the last digest. The fulfiller's digest lists items added and overdue. The requester's digest lists items completed and overdue. Greensheet sends no other email about changes.

### Event

An immutable record of something that happened on the instance: a greensheet or item was created, edited, completed, reopened, or archived; an invite was sent, accepted, or declined; a magic link was issued or consumed; a session was revoked; a person was deleted. The set of all events is the **audit log**. Greensheets and items are derived from events. Both parties to a greensheet can see its full history; the operator can see everything.

### Flip side

The second face of a greensheet: a greensheet with the same two people and the roles reversed, paired with the first for life. The original is the **front**. The fulfiller of the front creates the flip side by turning the sheet over with the **corner**; the requester cannot. A flip side has no flip side of its own. Each face is otherwise an ordinary greensheet with its own items, item numbers, history, and hard copy.

### Corner

The folded corner at the bottom right of a greensheet page. Clicking it turns the sheet over: to the other face if it exists, or, for the fulfiller of a front with no flip side yet, to the page that explains and offers to create one. The corner never appears on a hard copy and is not used for anything else.

## Explicit non-concepts

These are things Greensheet deliberately is not. Avoid vocabulary that implies them.

- **Shared task list.** There is no notion of multiple fulfillers, multiple requesters, or assignment.
- **Discussion or comment thread.** Communication about items happens in external channels.
- **Password or account registration.** Identity is an email address proven by magic link. There is nothing to sign up for.
- **Workflow or dependency.** No item blocks or depends on another.
- **Attachment or file host.** Documents travel by channel or URL, never through Greensheet.
- **Checklist, to-do list, task list.** These words imply the holder of the list can add to it. Do not use them for a greensheet. Use "greensheet", "item", and "expectation".
- **Reassignment.** A greensheet's requester and fulfiller never change.

## Candidate terms (not yet adopted)

- **Subtask**: a possible child of an item. Out for now; revisit later.
- **Export**: a possible way to get a greensheet's data out in bulk. Likely subsumed by the API; undecided.
- **Webhook**: the likely mechanism for outbound bridges. Not yet adopted as a term.
- **Server-side PDF**: a hard copy generated by the instance rather than the browser, for bridges or email. Not at launch.
