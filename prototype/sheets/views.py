from datetime import date
from functools import wraps

import segno
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from . import services
from .models import ApiToken, Greensheet, Person
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


def _item_response(request, sheet, role, item):
    if _is_htmx(request):
        return render(request, "sheets/_item.html", {"sheet": sheet, "role": role, "item": item})
    return redirect(sheet)


def _sheet_context(request, sheet, role):
    show_completed = request.session.get(f"show_completed:{sheet.code}", True)
    items = list(sheet.items.all())
    qr = segno.make(sheet.absolute_url, error="m").svg_data_uri(scale=4, border=1, dark="#111111", light=None)
    sub = services.digest_for(sheet, request.user)
    return {
        "sheet": sheet,
        "role": role,
        "items": items,
        "open_count": sum(1 for i in items if not i.complete),
        "done_count": sum(1 for i in items if i.complete),
        "show_completed": show_completed,
        "qr": qr,
        "digest": sub,
        "now": timezone.now(),
    }


# ---------------------------------------------------------------- sign in


@require_http_methods(["GET", "POST"])
def signin(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if "@" not in email:
            messages.error(request, "Enter your email address.")
            return redirect("signin")
        person, _ = Person.objects.get_or_create_by_email(email)
        link = services.issue_magic_link(person, request.GET.get("next") or "/")
        return render(
            request,
            "sheets/check_email.html",
            {"email": email, "link": link if settings.SHOW_MAGIC_LINKS else None},
        )
    return render(request, "sheets/signin.html")


def consume(request, token):
    link = services.consume_magic_link(token)
    if link is None:
        return render(request, "sheets/link_bad.html", status=410)
    login(request, link.person, backend="django.contrib.auth.backends.ModelBackend")
    nxt = link.next if link.next.startswith("/") else "/"
    return redirect(nxt)


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
    return render(
        request,
        "sheets/home.html",
        {
            "for_me": Greensheet.objects.filter(fulfiller=me).select_related("requester"),
            "set_by_me": Greensheet.objects.filter(requester=me).select_related("fulfiller"),
        },
    )


@login_required
@require_POST
def new_sheet(request):
    p = request.POST
    try:
        sheet = services.create_greensheet(
            request.user,
            name=p.get("name", ""),
            fulfiller_email=p.get("fulfiller_email", ""),
            fulfiller_name=p.get("fulfiller_name", ""),
            contact_email=p.get("contact_email", ""),
            contact_phone=p.get("contact_phone", ""),
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
def delete_me(request):
    if request.method == "POST" and request.POST.get("confirm") == request.user.email:
        person = request.user
        logout(request)
        services.delete_person(person)
        return render(request, "sheets/deleted.html")
    return render(request, "sheets/delete_me.html")


# ---------------------------------------------------------------- greensheet


@party
def sheet(request, sheet, role):
    if request.GET.get("completed") in ("show", "hide"):
        request.session[f"show_completed:{sheet.code}"] = request.GET["completed"] == "show"
        return redirect(sheet)
    return render(request, "sheets/sheet.html", _sheet_context(request, sheet, role))


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
            sheet, request.user, name=p.get("name"), contact_email=p.get("contact_email"), contact_phone=p.get("contact_phone")
        )
        return redirect(sheet)
    return render(request, "sheets/edit_sheet.html", {"sheet": sheet, "role": role})


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
            messages.error(request, str(e))
        return redirect(sheet)
    return render(request, "sheets/edit_item.html", {"sheet": sheet, "role": role, "item": item})


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
