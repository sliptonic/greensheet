from datetime import date, timedelta
from functools import wraps

import segno
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import services
from .models import ApiToken, Greensheet, MagicLink, Person, Visit, Webhook
from .services import Refused

# ---------------------------------------------------------------- helpers


def _sheet_for(request, code):
    sheet = get_object_or_404(
        Greensheet.objects.select_related("requester", "fulfiller"), code=code
    )
    role = sheet.role_for(request.user)
    if role is None:
        raise Http404
    return sheet, role


def party(view):
    """The signed-in person must be requester or fulfiller of the greensheet."""

    @wraps(view)
    @login_required
    def wrapped(request, code, *args, **kwargs):
        sheet, role = _sheet_for(request, code)
        return view(request, sheet, role, *args, **kwargs)

    return wrapped


def requester_only(view):
    @wraps(view)
    def wrapped(request, sheet, role, *args, **kwargs):
        if role != "requester":
            raise Http404
        return view(request, sheet, role, *args, **kwargs)

    return wrapped


def _safe_next(path):
    """A local path to return to after sign-in, else the home page."""
    path = path or ""
    return path if path.startswith("/") and not path.startswith("//") else "/"


def _is_htmx(request):
    return request.headers.get("HX-Request") == "true"


def _parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise Refused("Enter the due date as YYYY-MM-DD.")


def _site_url(request):
    """The public address of this instance as this page should print it."""
    if settings.SITE_URL_EXPLICIT:
        return settings.SITE_URL
    return request.build_absolute_uri("/").rstrip("/")


def _show_completed(request, sheet):
    """Completed items are hidden unless this person chose to see them."""
    return request.session.get(f"show_completed:{sheet.code}", False)


def _counts(sheet):
    items = list(sheet.items.all())
    done = sum(1 for i in items if i.complete)
    return items, len(items) - done, done


def _item_response(request, sheet, role, item):
    if _is_htmx(request):
        items, open_count, done_count = _counts(sheet)
        show = _show_completed(request, sheet)
        return render(
            request,
            "sheets/_item_swap.html",
            {
                "sheet": sheet,
                "role": role,
                "item": item,
                # A newly completed item leaves the list when completed items are hidden.
                "leaving": item.complete and not show,
                "items": items,
                "open_count": open_count,
                "done_count": done_count,
                "show_completed": show,
            },
        )
    return redirect(sheet)


# A visit lasts this long: refreshing within it keeps the "new" tags; the
# next visit after it starts a fresh baseline.
VISIT_WINDOW = timedelta(minutes=10)


def _mark_new(request, sheet, role, items, preview):
    """Tag items added since this person's previous visit. Fulfiller only:
    the requester added them. Nothing is recorded for a preview."""
    if preview:
        return
    now = timezone.now()
    visit, created = Visit.objects.get_or_create(greensheet=sheet, person=request.user, defaults={"seen_at": now})
    if created:
        return
    since = visit.seen_at
    if now - since > VISIT_WINDOW:
        visit.seen_at = now
        visit.save(update_fields=["seen_at"])
    if role != "fulfiller":
        return
    for it in items:
        it.is_new = not it.complete and it.created_at > since


def _sheet_context(request, sheet, role, preview=False):
    show_completed = _show_completed(request, sheet)
    items, open_count, done_count = _counts(sheet)
    _mark_new(request, sheet, role, items, preview)
    sheet_url = _site_url(request) + sheet.get_absolute_url()
    qr = segno.make(sheet_url, error="m").svg_data_uri(scale=4, border=1, dark="#111111", light=None)
    sub = services.digest_for(sheet, request.user)
    paired = sheet.paired
    return {
        "sheet": sheet,
        "sheet_url": sheet_url,
        "sheet_short_url": sheet_url.split("://", 1)[-1],
        "role": role,
        "paired": paired,
        "preview": preview,
        "can_create_flip": paired is None and role == "fulfiller" and not sheet.is_flip_side and not preview,
        "flip_url": reverse("flip", args=[sheet.code]),
        "items": items,
        "open_count": open_count,
        "done_count": done_count,
        "show_completed": show_completed,
        "qr": qr,
        "digest": sub,
        "now": timezone.now(),
    }


# ---------------------------------------------------------------- sign in


@require_http_methods(["GET", "POST"])
def signin(request):
    """The destination travels in a hidden field on POST, not the query string.

    Proxies with a web application firewall tend to reject a POST whose
    query string carries a path, which is exactly what ?next=/s/<code> is.
    """
    nxt = _safe_next(request.POST.get("next") or request.GET.get("next"))
    if request.user.is_authenticated:
        return redirect(nxt)
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if "@" not in email:
            messages.error(request, "Enter your email address.")
            return render(request, "sheets/signin.html", {"next": nxt})
        if not services.cold_signin_allowed(email):
            messages.error(request, "This instance is by invitation. Ask someone here to set a greensheet for you.")
            return render(request, "sheets/signin.html", {"next": nxt})
        person, _ = Person.objects.get_or_create_by_email(email)
        try:
            link = services.issue_magic_link(person, nxt)
        except Refused as e:
            messages.error(request, str(e))
            return render(request, "sheets/signin.html", {"next": nxt})
        return render(
            request,
            "sheets/check_email.html",
            {"email": email, "link": link if settings.SHOW_MAGIC_LINKS else None},
        )
    return render(request, "sheets/signin.html", {"next": nxt})


def consume(request, token):
    link = services.consume_magic_link(token)
    if link is None:
        # Send them back where the dead link was going, so a stale link to a
        # greensheet lands on that greensheet's sign-in form.
        stale = MagicLink.objects.filter(token=token).values_list("next", flat=True).first()
        return render(request, "sheets/link_bad.html", {"next": _safe_next(stale)}, status=410)
    login(request, link.person, backend="django.contrib.auth.backends.ModelBackend")
    request.session["epoch"] = link.person.session_epoch
    return redirect(_safe_next(link.next))


@require_POST
def signout(request):
    logout(request)
    return redirect("signin")


def decline(request, token):
    invite = services.decline_invite(token)
    if invite is None:
        raise Http404
    return render(request, "sheets/declined.html", {"invite": invite})


# ---------------------------------------------------------------- home


@login_required
def home(request):
    me = request.user
    sheets = Greensheet.objects.select_related("requester", "fulfiller").annotate(
        open_items=Count("items", filter=Q(items__completed_at__isnull=True)),
        done_items=Count("items", filter=Q(items__completed_at__isnull=False)),
    )
    return render(
        request,
        "sheets/home.html",
        {
            "for_me": sheets.filter(fulfiller=me),
            "set_by_me": sheets.filter(requester=me),
            # ?from=<code> opens the form with that greensheet as the start.
            "copy_from": request.GET.get("from", ""),
        },
    )


@login_required
@require_POST
def new_sheet(request):
    p = request.POST
    copy_from = None
    if p.get("copy_from"):
        copy_from = get_object_or_404(Greensheet, code=p["copy_from"], requester=request.user)
    try:
        sheet = services.create_greensheet(
            request.user,
            copy_from=copy_from,
            name=p.get("name", ""),
            fulfiller_email=p.get("fulfiller_email", ""),
            fulfiller_name=p.get("fulfiller_name", ""),
            contact_email=p.get("contact_email", ""),
            contact_phone=p.get("contact_phone", ""),
            icon=p.get("icon", ""),
        )
    except Refused as e:
        messages.error(request, str(e))
        return redirect("home")
    if not request.user.name and p.get("your_name", "").strip():
        request.user.name = p["your_name"].strip()
        request.user.save(update_fields=["name"])
    return redirect(sheet)


@login_required
@require_http_methods(["GET", "POST"])
def tokens(request):
    new_key = None
    if request.method == "POST":
        if request.POST.get("revoke"):
            ApiToken.objects.filter(person=request.user, pk=request.POST["revoke"]).update(revoked_at=timezone.now())
        else:
            new_key = services.create_token(request.user, request.POST.get("label", "")).key
    return render(
        request,
        "sheets/tokens.html",
        {"tokens": request.user.api_tokens.filter(revoked_at__isnull=True), "new_key": new_key},
    )


@login_required
@require_http_methods(["GET", "POST"])
def webhooks(request):
    if request.method == "POST":
        if request.POST.get("delete"):
            hook = get_object_or_404(Webhook, person=request.user, pk=request.POST["delete"])
            services.delete_webhook(hook)
        else:
            try:
                services.create_webhook(request.user, request.POST.get("url", ""), request.POST.get("label", ""))
            except Refused as e:
                messages.error(request, str(e))
        return redirect("webhooks")
    return render(request, "sheets/webhooks.html", {"hooks": request.user.webhooks.order_by("created_at")})


@login_required
@require_http_methods(["GET", "POST"])
def delete_me(request):
    if request.method == "POST" and request.POST.get("confirm") == request.user.email:
        person = request.user
        logout(request)
        services.delete_person(person)
        return render(request, "sheets/deleted.html")
    return render(request, "sheets/delete_me.html")


# ---------------------------------------------------------------- greensheet


def sheet(request, code):
    """A greensheet's address is stable and is what the invite email carries.

    Signed out, the page asks for an email address and sends a sign-in link
    that returns here. The greensheet itself is not shown until then.
    """
    if not request.user.is_authenticated:
        return render(request, "sheets/sheet_signin.html", {"next": reverse("sheet", args=[code])})
    sheet, role = _sheet_for(request, code)
    if request.GET.get("completed") in ("show", "hide"):
        request.session[f"show_completed:{sheet.code}"] = request.GET["completed"] == "show"
        return redirect(sheet)
    preview = role == "requester" and request.GET.get("preview") == "1"
    if preview:
        role = "fulfiller"
    return render(request, "sheets/sheet.html", _sheet_context(request, sheet, role, preview=preview))


@party
def history(request, sheet, role):
    events = sheet.events.select_related("actor").order_by("at", "id")
    return render(request, "sheets/history.html", {"sheet": sheet, "role": role, "events": events})


@party
@requester_only
@require_http_methods(["GET", "POST"])
def edit_sheet(request, sheet, role):
    if request.method == "POST":
        p = request.POST
        services.edit_greensheet(
            sheet,
            request.user,
            name=p.get("name"),
            contact_email=p.get("contact_email"),
            contact_phone=p.get("contact_phone"),
            icon=p.get("icon"),
        )
        return redirect(sheet)
    return render(request, "sheets/edit_sheet.html", {"sheet": sheet, "role": role})


@party
@require_http_methods(["GET", "POST"])
def flip(request, sheet, role):
    """Turn the greensheet over. If the flip side exists, go there. If not
    and you are the fulfiller, explain and offer to create it."""
    paired = sheet.paired
    if paired is not None:
        return redirect(paired.get_absolute_url() + "?flipped=1")
    if role != "fulfiller" or sheet.is_flip_side:
        raise Http404
    if request.method == "POST":
        try:
            flip_sheet = services.create_flip_side(sheet, request.user)
        except Refused as e:
            messages.error(request, str(e))
            return redirect(sheet)
        return redirect(flip_sheet.get_absolute_url() + "?flipped=1")
    return render(request, "sheets/flip.html", {"sheet": sheet, "role": role})


@party
@requester_only
@require_POST
def revoke(request, sheet, role):
    target = services.revoke_sessions(sheet, request.user)
    messages.success(request, f"{target.display} has been signed out everywhere.")
    return redirect(sheet)


@party
@requester_only
@require_POST
def archive(request, sheet, role):
    services.archive(sheet, request.user)
    return redirect(sheet)


@party
@requester_only
@require_POST
def unarchive(request, sheet, role):
    services.unarchive(sheet, request.user)
    return redirect(sheet)


@party
@require_POST
def digest_toggle(request, sheet, role):
    services.toggle_digest(sheet, request.user)
    return redirect(sheet)


@party
def digest_off(request, sheet, role):
    sub = services.digest_for(sheet, request.user)
    if sub.enabled:
        services.toggle_digest(sheet, request.user)
    messages.success(request, "Daily summary turned off for this greensheet.")
    return redirect(sheet)


# ---------------------------------------------------------------- items


@party
@requester_only
@require_POST
def add_item(request, sheet, role):
    p = request.POST
    try:
        services.add_item(sheet, request.user, title=p.get("title", ""), note=p.get("note", ""), due_date=_parse_date(p.get("due_date")))
    except Refused as e:
        messages.error(request, str(e))
    return redirect(sheet)


def _item(sheet, number):
    return get_object_or_404(sheet.items, number=number)


@party
@require_POST
def complete(request, sheet, role, number):
    item = _item(sheet, number)
    try:
        services.complete_item(item, request.user)
    except Refused as e:
        return HttpResponseBadRequest(str(e))
    return _item_response(request, sheet, role, item)


@party
@require_POST
def reopen(request, sheet, role, number):
    item = _item(sheet, number)
    try:
        services.reopen_item(item, request.user)
    except Refused as e:
        return HttpResponseBadRequest(str(e))
    return _item_response(request, sheet, role, item)


@party
@requester_only
@require_http_methods(["GET", "POST"])
def edit_item(request, sheet, role, number):
    """Edit in place over htmx: GET swaps the row for a form, POST swaps it
    back. Without htmx the same URL is an ordinary page."""
    item = _item(sheet, number)
    if request.method == "POST":
        p = request.POST
        try:
            services.edit_item(
                item,
                request.user,
                title=p.get("title"),
                note=p.get("note"),
                due_date=_parse_date(p.get("due_date")),
                clear_due=not p.get("due_date", "").strip(),
            )
        except Refused as e:
            if _is_htmx(request):
                return HttpResponseBadRequest(str(e))
            messages.error(request, str(e))
            return redirect(sheet)
        return _item_response(request, sheet, role, item)
    ctx = {"sheet": sheet, "role": role, "item": item}
    if _is_htmx(request):
        return render(request, "sheets/_item_edit.html", ctx)
    return render(request, "sheets/edit_item.html", ctx)


@party
def item_row(request, sheet, role, number):
    """One item as it appears on the sheet. Cancel in the in-place editor."""
    item = _item(sheet, number)
    if _is_htmx(request):
        return render(request, "sheets/_item.html", {"sheet": sheet, "role": role, "item": item})
    return redirect(sheet)


@party
@requester_only
@require_POST
def delete_item(request, sheet, role, number):
    item = _item(sheet, number)
    try:
        services.delete_item(item, request.user)
    except Refused as e:
        messages.error(request, str(e))
    if _is_htmx(request):
        return HttpResponse("")
    return redirect(sheet)
