"""
Every state change goes through here and writes an event. Views and the API
are thin wrappers over these functions.
"""

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .icons import clean_icon

from . import webhooks
from .models import (
    ApiToken,
    Block,
    DigestSubscription,
    Event,
    Greensheet,
    Invite,
    Item,
    MagicLink,
    Person,
    Webhook,
)


class Refused(Exception):
    """A request the spec says no to. The message is safe to show the person."""


# ---------------------------------------------------------------- events


def record(kind, *, greensheet=None, item=None, actor=None, **data):
    if greensheet is not None:
        data.setdefault("sheet_code", greensheet.code)
        data.setdefault("sheet_name", greensheet.name)
    if item is not None:
        data.setdefault("item_number", item.number)
        data.setdefault("item_title", item.title)
    if actor is not None:
        data.setdefault("actor", actor.display)
    event = Event.objects.create(kind=kind, greensheet=greensheet, item=item, actor=actor, data=data)
    if greensheet is not None:
        transaction.on_commit(lambda: webhooks.deliver(event))
    return event


# ---------------------------------------------------------------- email

def _send(to, subject, body):
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)


def subject_for(sheet, suffix=""):
    """Subject grammar from docs/DESIGN.md: 'Greensheet: <name>' plus a fixed suffix."""
    s = f"Greensheet: {sheet.name}"
    return f"{s}{suffix}" if suffix else s


# ---------------------------------------------------------------- sign in


def cold_signin_allowed(email):
    """Open instance unless an allowlist is set. Invited people always pass."""
    if not settings.ALLOWLIST:
        return True
    email = Person.objects.normalize(email)
    if Person.objects.filter(email=email).exists():
        return True
    domain = email.rsplit("@", 1)[-1]
    return email in settings.ALLOWLIST or domain in settings.ALLOWLIST


def issue_magic_link(person, next_path="/", send=True):
    recent = MagicLink.objects.filter(person=person, created_at__gte=timezone.now() - timedelta(hours=1)).count()
    if recent >= settings.MAGIC_LINKS_PER_HOUR:
        raise Refused("Too many sign-in links have been sent to that address in the last hour. Try again later.")
    link = MagicLink.objects.create(person=person, next=next_path or "/")
    record("link.issued", actor=person)
    if send:
        body = (
            "Sign in to Greensheet\n"
            "\n"
            "Open this link on the device you want to use. It works once and\n"
            f"expires in {settings.MAGIC_LINK_TTL_MINUTES} minutes.\n"
            "\n"
            f"{link.absolute_url}\n"
            "\n"
            "If you did not ask for this, ignore it.\n"
        )
        _send(person.email, "Greensheet: sign in", body)
    return link


def consume_magic_link(token):
    try:
        link = MagicLink.objects.select_related("person").get(token=token)
    except MagicLink.DoesNotExist:
        return None
    if not link.usable:
        return None
    link.consumed_at = timezone.now()
    link.save(update_fields=["consumed_at"])
    record("link.consumed", actor=link.person)
    # Accept any pending invite for this person the moment they sign in.
    for inv in Invite.objects.filter(
        greensheet__fulfiller=link.person, accepted_at__isnull=True, declined_at__isnull=True
    ).select_related("greensheet"):
        inv.accepted_at = timezone.now()
        inv.save(update_fields=["accepted_at"])
        record("invite.accepted", greensheet=inv.greensheet, actor=link.person)
    return link


# ---------------------------------------------------------------- greensheets


def _fulfiller_for(requester, email, name=""):
    """The person a greensheet is for, after the checks that guard an invite."""
    fulfiller, _ = Person.objects.get_or_create_by_email(email, name)
    if fulfiller.id == requester.id:
        raise Refused("A greensheet is for someone else. Enter another person's email.")
    if Block.objects.filter(requester=requester, person=fulfiller).exists():
        raise Refused("That person has declined greensheets from you.")
    since = timezone.now() - timedelta(days=1)
    sent_today = Event.objects.filter(kind="invite.sent", actor=requester, at__gte=since).count()
    if sent_today >= settings.DAILY_INVITE_CAP:
        raise Refused("You have sent as many invites as this instance allows in a day. Try tomorrow.")
    return fulfiller


@transaction.atomic
def create_greensheet(
    requester, *, name, fulfiller_email="", fulfiller_name="", contact_email="", contact_phone="", icon="", copy_from=None
):
    """Set a greensheet for someone, or save a draft to send later.

    Without a fulfiller email the greensheet is a draft: only the requester
    sees it, nothing is sent, and it can be sent later or used to start
    others from. With copy_from, one of the requester's own greensheets,
    the items come along: titles, notes, and due dates kept at the same
    distance from today as they were from that greensheet's start.
    The same list for every new hire, every client, every tenant."""
    name = name.strip()
    if not name:
        raise Refused("Give the greensheet a name.")
    if copy_from is not None and copy_from.requester_id != requester.id:
        raise Refused("You can only start from a greensheet you created.")
    fulfiller = _fulfiller_for(requester, fulfiller_email, fulfiller_name) if fulfiller_email.strip() else None

    sheet = Greensheet.objects.create(
        name=name,
        # Left blank, the icon comes along from the starting greensheet.
        icon=clean_icon(icon) or (copy_from.icon if copy_from is not None else ""),
        requester=requester,
        fulfiller=fulfiller,
        contact_email=(contact_email or requester.email).strip().lower(),
        contact_phone=contact_phone.strip(),
    )
    data = {}
    if copy_from is not None:
        data["copied_from"] = copy_from.code
    if fulfiller is None:
        data["draft"] = True
    record("sheet.created", greensheet=sheet, actor=requester, **data)
    if copy_from is not None:
        _copy_items(copy_from, sheet, requester)
    if fulfiller is not None:
        invite = Invite.objects.create(greensheet=sheet)
        send_invite(invite)
    return sheet


@transaction.atomic
def send_greensheet(sheet, actor, *, fulfiller_email, fulfiller_name=""):
    """A draft becomes a greensheet for someone: the invite goes out now."""
    if not sheet.is_draft:
        raise Refused("This greensheet has already been sent.")
    if actor.id != sheet.requester_id:
        raise Refused("Only the requester can send a greensheet.")
    _writable(sheet)
    if "@" not in (fulfiller_email or ""):
        raise Refused("Enter their email address.")
    sheet.fulfiller = _fulfiller_for(actor, fulfiller_email, fulfiller_name)
    sheet.save(update_fields=["fulfiller"])
    record("sheet.sent", greensheet=sheet, actor=actor, to=sheet.fulfiller.email)
    invite = Invite.objects.create(greensheet=sheet)
    send_invite(invite)
    return sheet


def _copy_items(source, sheet, actor):
    start = timezone.localdate()
    since = timezone.localtime(source.created_at).date()
    for it in source.items.order_by("number"):
        due = None
        if it.due_date and it.due_date >= since:
            due = start + (it.due_date - since)
        add_item(sheet, actor, title=it.title, note=it.note, due_date=due)


def send_invite(invite):
    """The invite links to the greensheet itself, an address that never changes.

    No magic link: the fulfiller signs in from the greensheet page when they
    get there, however long that takes, and the same email works again later.
    """
    sheet = invite.greensheet
    decline = settings.SITE_URL + reverse("decline", args=[invite.token])
    lines = [
        f"{sheet.name}",
        f"From {sheet.requester.display}",
        "",
        f"{sheet.requester.display} has set out some things they need from you.",
        "Open the greensheet, and mark each item when it is done.",
        "",
        f"{sheet.absolute_url}",
        "",
        "The first time, enter your email address and a sign-in link will arrive.",
        "There is no password. Keep this email: the address above always works.",
        "",
        f"If you don't want greensheets from {sheet.requester.display}, decline here:",
        f"{decline}",
        "",
    ]
    _send(sheet.fulfiller.email, subject_for(sheet, f" from {sheet.requester.display}"), "\n".join(lines))
    record("invite.sent", greensheet=sheet, actor=sheet.requester, to=sheet.fulfiller.email)
    return invite


@transaction.atomic
def decline_invite(token):
    try:
        invite = Invite.objects.select_related("greensheet__requester", "greensheet__fulfiller").get(token=token)
    except Invite.DoesNotExist:
        return None
    sheet = invite.greensheet
    if invite.declined_at is None:
        invite.declined_at = timezone.now()
        invite.save(update_fields=["declined_at"])
        Block.objects.get_or_create(requester=sheet.requester, person=sheet.fulfiller)
        record("invite.declined", greensheet=sheet, actor=sheet.fulfiller)
    return invite


def edit_greensheet(sheet, actor, *, name=None, contact_email=None, contact_phone=None, icon=None):
    changed = {}
    if name is not None and name.strip() and name.strip() != sheet.name:
        changed["name"] = [sheet.name, name.strip()]
        sheet.name = name.strip()
    if icon is not None and clean_icon(icon) != sheet.icon:
        changed["icon"] = [sheet.icon, clean_icon(icon)]
        sheet.icon = clean_icon(icon)
    if contact_email is not None and contact_email.strip() and contact_email.strip().lower() != sheet.contact_email:
        changed["contact_email"] = [sheet.contact_email, contact_email.strip().lower()]
        sheet.contact_email = contact_email.strip().lower()
    if contact_phone is not None and contact_phone.strip() != sheet.contact_phone:
        changed["contact_phone"] = [sheet.contact_phone, contact_phone.strip()]
        sheet.contact_phone = contact_phone.strip()
    if changed:
        sheet.save()
        record("sheet.edited", greensheet=sheet, actor=actor, changed=changed)
    return sheet


def archive(sheet, actor):
    if not sheet.archived:
        sheet.archived_at = timezone.now()
        sheet.save(update_fields=["archived_at"])
        record("sheet.archived", greensheet=sheet, actor=actor)


def unarchive(sheet, actor):
    if sheet.archived:
        sheet.archived_at = None
        sheet.save(update_fields=["archived_at"])
        record("sheet.unarchived", greensheet=sheet, actor=actor)


def _writable(sheet):
    if sheet.archived:
        raise Refused("This greensheet is archived. Unarchive it to make changes.")


def revoke_sessions(sheet, actor):
    """Sign the other party out everywhere. They sign back in by magic link."""
    target = sheet.other_party(actor)
    target.session_epoch += 1
    target.save(update_fields=["session_epoch"])
    record("session.revoked", greensheet=sheet, actor=actor, who=target.display)
    return target


# ---------------------------------------------------------------- flip side


@transaction.atomic
def create_flip_side(sheet, actor):
    """The fulfiller turns the greensheet over and sets out what they need
    from the requester. Same two people, roles reversed, paired for life."""
    if sheet.is_draft:
        raise Refused("A draft has no flip side until it is sent.")
    if sheet.is_flip_side:
        raise Refused("This is already the flip side. Turn it back over to see the front.")
    if sheet.paired is not None:
        return sheet.paired
    if actor.id != sheet.fulfiller_id:
        raise Refused("Only the fulfiller can create the flip side.")
    if sheet.requester.is_placeholder:
        raise Refused("The requester has deleted their account.")
    name = f"Flip side of {sheet.name}"[:200]
    flip = Greensheet.objects.create(
        name=name,
        icon=sheet.icon,
        requester=sheet.fulfiller,
        fulfiller=sheet.requester,
        contact_email=actor.email,
        contact_phone="",
        flip_of=sheet,
    )
    # The other party is already here; no invite email. The record keeps the
    # invite flow consistent.
    Invite.objects.create(greensheet=flip, accepted_at=timezone.now())
    record("flip.created", greensheet=sheet, actor=actor, flip_code=flip.code)
    record("sheet.created", greensheet=flip, actor=actor, flip_of=sheet.code)
    return flip


# ---------------------------------------------------------------- items


@transaction.atomic
def add_item(sheet, actor, *, title, note="", due_date=None):
    _writable(sheet)
    title = title.strip()
    if not title:
        raise Refused("An item needs a title.")
    sheet = Greensheet.objects.select_for_update().get(pk=sheet.pk)
    item = Item.objects.create(
        greensheet=sheet, number=sheet.next_item_number, title=title, note=note.strip(), due_date=due_date or None
    )
    sheet.next_item_number += 1
    sheet.save(update_fields=["next_item_number"])
    record("item.created", greensheet=sheet, item=item, actor=actor)
    return item


def edit_item(item, actor, *, title=None, note=None, due_date=None, clear_due=False):
    _writable(item.greensheet)
    changed = {}
    if title is not None and title.strip() and title.strip() != item.title:
        changed["title"] = [item.title, title.strip()]
        item.title = title.strip()
    if note is not None and note.strip() != item.note:
        changed["note"] = True
        item.note = note.strip()
    if clear_due and item.due_date:
        changed["due_date"] = [str(item.due_date), None]
        item.due_date = None
    elif due_date and due_date != item.due_date:
        changed["due_date"] = [str(item.due_date) if item.due_date else None, str(due_date)]
        item.due_date = due_date
    if changed:
        item.save()
        record("item.edited", greensheet=item.greensheet, item=item, actor=actor, changed=changed)
    return item


def delete_item(item, actor):
    _writable(item.greensheet)
    record("item.deleted", greensheet=item.greensheet, item=item, actor=actor)
    item.delete()


def complete_item(item, actor):
    _writable(item.greensheet)
    if not item.complete:
        item.completed_at = timezone.now()
        item.completed_by = actor
        item.save(update_fields=["completed_at", "completed_by"])
        record("item.completed", greensheet=item.greensheet, item=item, actor=actor)
    return item


def reopen_item(item, actor):
    _writable(item.greensheet)
    if item.complete:
        item.completed_at = None
        item.completed_by = None
        item.save(update_fields=["completed_at", "completed_by"])
        record("item.reopened", greensheet=item.greensheet, item=item, actor=actor)
    return item


# ---------------------------------------------------------------- digest


def digest_for(sheet, person):
    sub, _ = DigestSubscription.objects.get_or_create(greensheet=sheet, person=person)
    return sub


def toggle_digest(sheet, person):
    sub = digest_for(sheet, person)
    sub.enabled = not sub.enabled
    sub.save(update_fields=["enabled"])
    record("digest.on" if sub.enabled else "digest.off", greensheet=sheet, actor=person)
    return sub


def compose_digest(sub):
    """Return (subject, body) or None if there is nothing to say.

    The fulfiller hears about items added and overdue. The requester hears
    about items completed and overdue. Nothing else.
    """
    sheet = sub.greensheet
    person = sub.person
    role = sheet.role_for(person)
    since = sub.last_sent_at or (timezone.now() - timedelta(days=1))
    events = sheet.events.filter(at__gt=since)
    items = {i.number: i for i in sheet.items.all()}

    added = []
    completed = []
    if role == "fulfiller":
        for e in events.filter(kind="item.created").order_by("at"):
            it = items.get(e.data.get("item_number"))
            if it:
                added.append(it)
    if role == "requester":
        for e in events.filter(kind="item.completed").order_by("at"):
            it = items.get(e.data.get("item_number"))
            if it and it.complete:
                completed.append(it)
    overdue = [i for i in sheet.items.all() if i.overdue]

    if not (added or completed or overdue):
        return None

    parts = []
    if added:
        parts.append(f"{len(added)} new")
    if completed:
        parts.append(f"{len(completed)} completed")
    if overdue:
        parts.append(f"{len(overdue)} overdue")
    subject = subject_for(sheet, ", " + ", ".join(parts))

    def line(it):
        s = f"  {it.number:>2}  {it.title}"
        if it.due_date:
            s += f"\n      due {it.due_date:%a, %b %-d}"
        return s

    out = [sheet.name, f"From {sheet.requester.display}", ""]
    if added:
        out.append(f"{len(added)} item{'s' if len(added) != 1 else ''} added since yesterday.")
        out.append("")
        out.extend(line(i) for i in added)
        out.append("")
    if completed:
        out.append(f"{len(completed)} item{'s' if len(completed) != 1 else ''} completed.")
        out.append("")
        out.extend(line(i) for i in completed)
        out.append("")
    if overdue:
        out.append("Past due:")
        out.append("")
        out.extend(line(i) for i in overdue)
        out.append("")
    out.append("Open the greensheet:")
    out.append(sheet.absolute_url)
    out.append("")
    out.append("You asked for a daily summary of this greensheet.")
    out.append("Stop: " + settings.SITE_URL + reverse("digest_off", args=[sheet.code]))
    return subject, "\n".join(out) + "\n"


def send_digest(sub):
    composed = compose_digest(sub)
    sub.last_sent_at = timezone.now()
    sub.save(update_fields=["last_sent_at"])
    if not composed:
        return False
    subject, body = composed
    _send(sub.person.email, subject, body)
    record("digest.sent", greensheet=sub.greensheet, to=sub.person.email)
    return True


# ---------------------------------------------------------------- tokens


def create_token(person, label=""):
    token = ApiToken.objects.create(person=person, label=label.strip())
    record("token.created", actor=person, label=token.label)
    return token


# ---------------------------------------------------------------- webhooks


def create_webhook(person, url, label=""):
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise Refused("The webhook URL must start with http:// or https://.")
    hook = Webhook.objects.create(person=person, url=url, label=label.strip())
    record("webhook.created", actor=person, label=hook.label, url=url)
    return hook


def delete_webhook(hook):
    record("webhook.deleted", actor=hook.person, label=hook.label, url=hook.url)
    hook.delete()


# ---------------------------------------------------------------- deletion


@transaction.atomic
def delete_person(person):
    """Greensheets they own are deleted. Greensheets they fulfill survive with
    a placeholder. Events remain."""
    for sheet in list(person.sheets_set.all()):
        record("sheet.deleted", greensheet=sheet, actor=person)
        sheet.delete()
    if person.sheets_for.exists():
        placeholder = Person.objects.create(
            email=f"deleted-{person.id}@invalid", name="Deleted person", is_active=False, is_placeholder=True
        )
        placeholder.set_unusable_password()
        placeholder.save(update_fields=["password"])
        person.sheets_for.update(fulfiller=placeholder)
    record("person.deleted", actor=None, actor_name=person.display, email_hash=str(person.id))
    person.delete()
