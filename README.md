# Greensheet

Greensheet is a tool for setting, managing, and clarifying expectations between two people.

A greensheet is a set of expectations one person (the requester) sets for another (the fulfiller). A parent might set out chores for a child. A contractor might set out what a client must provide before work can begin.

## Why green

The name comes from an organization where busy people kept dropping important items. The fix was a sheet of expectations printed on green paper and handed out routinely. Within weeks, the green sheets were recognizable in the noise. People knew what one meant the moment they saw it and didn't have to work out the context.

Greensheet is that experience in a browser. A greensheet should be recognizable in an instant among your open tabs and in your inbox, without being noisy. It should look the same every time, ask for one thing, and never surprise you. Low cognitive burden, high trust.

## How it works

1. Sign in with your email address. There are no passwords and nothing to register. A link arrives in your inbox and signs you in on that device.
2. Create a greensheet and add items. Each item has a title, an optional note, an optional due date, and channels: ways to reach you about that item, such as email, SMS, or a messaging app.
3. Invite the fulfiller by email. They get the greensheet's address, which never changes. The first time they open it, they enter their email and a sign-in link arrives. The invite email works again whenever they need to find their way back.
4. The fulfiller works through the list. For each item they can mark it complete, or start a conversation with you through one of the channels you provided.
5. Add items any time. They appear to the fulfiller immediately, and in the next daily digest if they've opted in.

A greensheet can live for a long time, with items added and completed as the relationship goes on. When it's finished, archive it. Both of you can still see it, but nothing changes.

It has two faces. If you're the one being asked, turn the sheet over with the folded corner and set out what you need from them. The flip side works exactly the same way, with the roles reversed.

It is also a sheet. Print it. Either of you gets a clean hard copy in one click, with boxes to tick, contact details spelled out, and a code that leads back to the live greensheet. You can hand a printed greensheet to someone as their invitation.

Anyone can be a requester. If someone sends you a greensheet, you can set one for anyone else too.

## What it is not

- Not a shared task list. Each greensheet has exactly one requester and exactly one fulfiller.
- Not a chat or messaging app. Discussion about items happens elsewhere, through the channels on each item.
- Not a workflow tool. Items have no dependencies on each other.
- Not a file host. Documents travel through email or links, not through Greensheet.
- Not a to-do app. The fulfiller cannot add to the list. Only the requester can.

## Design goals

- Works in a browser for everyone. Nothing to install.
- Low friction to get started. Sign in from any device with just an email address.
- Reasonable security. Strangers can't spam you: one invite per sheet, and a one-click decline that blocks the sender.
- Everything logged. Both parties can see the full history of their greensheet.
- Your data is yours. Delete your account and your greensheets go with it.
- Simple to self-host. One process, one database file, and an outbound email account.
- Built to connect. Everything the web page can do, an API can do. New channels and bridges to other systems plug in without changing the core.
- Recognizable and quiet. One green mark, one page layout, one email subject grammar. No badges, no streaks, no red.
- Prints beautifully. The paper version is the original, not an afterthought.

## Status

First release. The application is in `app/`. Not a commercial product. Licensing undecided.
