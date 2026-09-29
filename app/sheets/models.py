"""
Data model. Vocabulary follows UBIQUITOUS_LANGUAGE.md.

Prototype simplification: greensheets and items are ordinary rows, and the
event log is written alongside them by the service layer rather than being
the source they are derived from.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.urls import reverse
from django.utils import timezone

# No ambiguous characters. Codes appear on paper and get typed by hand.
CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def short_code(length=6):
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))


def new_token():
    return secrets.token_urlsafe(32)


class PersonManager(BaseUserManager):
    def normalize(self, email):
        return self.normalize_email(email).strip().lower()

    def get_or_create_by_email(self, email, name=""):
        email = self.normalize(email)
        person, created = self.get_or_create(email=email, defaults={"name": name.strip()})
        if created:
            person.set_unusable_password()
            person.save(update_fields=["password"])
        return person, created

    def create_user(self, email, password=None, **extra):
        person = self.model(email=self.normalize(email), **extra)
        person.set_unusable_password()
        person.save()
        return person

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        person = self.model(email=self.normalize(email), **extra)
        if password:
            person.set_password(password)
        else:
            person.set_unusable_password()
        person.save()
        return person


class Person(AbstractBaseUser, PermissionsMixin):
    """A human known to the instance, identified by email. No passwords."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_placeholder = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    # Bumped to sign this person out everywhere. Sessions carry the value
    # they were created with; a mismatch ends the session.
    session_epoch = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    objects = PersonManager()

    class Meta:
        verbose_name_plural = "people"

    def __str__(self):
        return self.display

    @property
    def display(self):
        return self.name or self.email


class Greensheet(models.Model):
    code = models.CharField(max_length=12, unique=True, default=short_code)
    name = models.CharField(max_length=200)
    # One character or emoji the requester chose, drawn on the green mark so
    # this greensheet's tab and row stand out from the others. Blank: plain mark.
    icon = models.CharField(max_length=16, blank=True, default="")
    requester = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="sheets_set")
    fulfiller = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="sheets_for")
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    archived_at = models.DateTimeField(null=True, blank=True)
    next_item_number = models.PositiveIntegerField(default=1)
    # The flip side: a greensheet with the roles reversed, paired with this
    # one. Only an original has a flip side; a flip side points at its original.
    flip_of = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="flip_side"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def is_flip_side(self):
        return self.flip_of_id is not None

    @property
    def paired(self):
        """The other face of this greensheet, or None."""
        if self.flip_of_id:
            return self.flip_of
        try:
            return self.flip_side
        except Greensheet.DoesNotExist:
            return None

    def other_party(self, person):
        return self.fulfiller if person.id == self.requester_id else self.requester

    @property
    def archived(self):
        return self.archived_at is not None

    def role_for(self, person):
        if person is None or not person.is_authenticated:
            return None
        if person.id == self.requester_id:
            return "requester"
        if person.id == self.fulfiller_id:
            return "fulfiller"
        return None

    def get_absolute_url(self):
        return reverse("sheet", args=[self.code])

    @property
    def absolute_url(self):
        return settings.SITE_URL + self.get_absolute_url()

    @property
    def short_url(self):
        return self.absolute_url.replace("https://", "").replace("http://", "")


class Item(models.Model):
    greensheet = models.ForeignKey(Greensheet, on_delete=models.CASCADE, related_name="items")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=300)
    note = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["greensheet", "number"], name="item_number_unique_per_sheet")
        ]

    def __str__(self):
        return f"{self.number}. {self.title}"

    @property
    def complete(self):
        return self.completed_at is not None

    @property
    def overdue(self):
        return bool(self.due_date) and not self.complete and self.due_date < timezone.localdate()


class Invite(models.Model):
    greensheet = models.OneToOneField(Greensheet, on_delete=models.CASCADE, related_name="invite")
    token = models.CharField(max_length=64, unique=True, default=new_token)
    sent_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)


class Block(models.Model):
    """A declined invite blocks that requester from inviting that person again."""

    requester = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="blocks_out")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="blocks_in")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["requester", "person"], name="block_unique")]


class MagicLink(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="magic_links")
    token = models.CharField(max_length=64, unique=True, default=new_token)
    next = models.CharField(max_length=500, default="/")
    created_at = models.DateTimeField(default=timezone.now)
    consumed_at = models.DateTimeField(null=True, blank=True)

    @property
    def expired(self):
        ttl = timedelta(minutes=settings.MAGIC_LINK_TTL_MINUTES)
        return timezone.now() - self.created_at > ttl

    @property
    def usable(self):
        return self.consumed_at is None and not self.expired

    @property
    def absolute_url(self):
        return settings.SITE_URL + reverse("consume", args=[self.token])


class Visit(models.Model):
    """When a person last opened a greensheet. Items added since are marked
    new for the fulfiller. Not shown to the other party; it is not a read receipt."""

    greensheet = models.ForeignKey(Greensheet, on_delete=models.CASCADE, related_name="visits")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="visits")
    seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["greensheet", "person"], name="visit_unique")]


class DigestSubscription(models.Model):
    greensheet = models.ForeignKey(Greensheet, on_delete=models.CASCADE, related_name="digests")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="digests")
    enabled = models.BooleanField(default=False)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["greensheet", "person"], name="digest_unique")]


class Webhook(models.Model):
    """Outbound bridge. Every event on a greensheet the person is party to is
    POSTed to the URL, signed with the secret."""

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="webhooks")
    url = models.URLField(max_length=500)
    label = models.CharField(max_length=100, blank=True)
    secret = models.CharField(max_length=64, default=new_token)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_at = models.DateTimeField(null=True, blank=True)
    last_status = models.IntegerField(null=True, blank=True)
    last_error = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.label or self.url


class ApiToken(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="api_tokens")
    key = models.CharField(max_length=64, unique=True, default=new_token)
    label = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)


class Event(models.Model):
    """Immutable record of something that happened. The audit log.

    Foreign keys are SET_NULL so events outlive the rows they describe; the
    data field keeps the names and numbers a reader needs.
    """

    KINDS = [
        ("sheet.created", "greensheet created"),
        ("sheet.edited", "greensheet edited"),
        ("sheet.archived", "greensheet archived"),
        ("sheet.unarchived", "greensheet unarchived"),
        ("sheet.deleted", "greensheet deleted"),
        ("item.created", "item added"),
        ("item.edited", "item edited"),
        ("item.completed", "item completed"),
        ("item.reopened", "item reopened"),
        ("item.deleted", "item deleted"),
        ("invite.sent", "invite sent"),
        ("invite.accepted", "invite accepted"),
        ("invite.declined", "invite declined"),
        ("link.issued", "sign-in link sent"),
        ("link.consumed", "signed in"),
        ("digest.on", "daily summary turned on"),
        ("digest.off", "daily summary turned off"),
        ("digest.sent", "daily summary sent"),
        ("token.created", "API token created"),
        ("person.deleted", "person deleted"),
        ("flip.created", "flip side created"),
        ("session.revoked", "signed out everywhere"),
        ("webhook.created", "webhook created"),
        ("webhook.deleted", "webhook deleted"),
    ]

    at = models.DateTimeField(default=timezone.now, db_index=True)
    kind = models.CharField(max_length=40, choices=KINDS)
    greensheet = models.ForeignKey(
        Greensheet, null=True, blank=True, on_delete=models.SET_NULL, related_name="events"
    )
    item = models.ForeignKey(Item, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    actor = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-at", "-id"]

    def __str__(self):
        return f"{self.at:%Y-%m-%d %H:%M} {self.kind}"

    @property
    def actor_name(self):
        if self.actor:
            return self.actor.display
        return self.data.get("actor") or "someone"

    @property
    def item_label(self):
        n = self.data.get("item_number")
        t = self.data.get("item_title")
        if n and t:
            return f"item {n}, {t}"
        if n:
            return f"item {n}"
        return ""

    @property
    def description(self):
        """Plain sentence for the history page. Uses the ubiquitous language."""
        who = self.actor_name
        k = self.kind
        it = self.item_label
        if k == "sheet.created":
            return f"{who} created the greensheet"
        if k == "sheet.edited":
            return f"{who} edited the greensheet"
        if k == "sheet.archived":
            return f"{who} archived the greensheet"
        if k == "sheet.unarchived":
            return f"{who} unarchived the greensheet"
        if k == "item.created":
            return f"{who} added {it}"
        if k == "item.edited":
            return f"{who} edited {it}"
        if k == "item.completed":
            return f"{who} completed {it}"
        if k == "item.reopened":
            return f"{who} reopened {it}"
        if k == "item.deleted":
            return f"{who} deleted {it}"
        if k == "invite.sent":
            return f"{who} invited {self.data.get('to', 'the fulfiller')}"
        if k == "invite.accepted":
            return f"{who} accepted the invite"
        if k == "invite.declined":
            return f"{who} declined the invite"
        if k == "digest.on":
            return f"{who} turned on the daily summary"
        if k == "digest.off":
            return f"{who} turned off the daily summary"
        if k == "digest.sent":
            return f"daily summary sent to {self.data.get('to', '')}".strip()
        if k == "link.consumed":
            return f"{who} signed in"
        if k == "flip.created":
            return f"{who} created the flip side"
        if k == "session.revoked":
            return f"{who} signed {self.data.get('who', 'the other party')} out everywhere"
        return f"{who}: {self.get_kind_display()}"
