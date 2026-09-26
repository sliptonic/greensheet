"""
Minimal JSON API. Same service layer as the web views. Authenticate with
`Authorization: Bearer <token>`; tokens are created at /me/tokens.

    GET  /api/sheets                      greensheets the token holder is party to
    GET  /api/sheets/<code>               one greensheet with its items
    POST /api/sheets/<code>/items         add an item (requester only)
    POST /api/sheets/<code>/items/<n>/complete
    POST /api/sheets/<code>/items/<n>/reopen
    GET  /api/sheets/<code>/events        the audit log for that greensheet
"""

import json
from functools import wraps

from django.http import Http404, JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import services
from .models import ApiToken, Greensheet
from .services import Refused


def _person(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        return ApiToken.objects.select_related("person").get(key=auth[7:].strip(), revoked_at__isnull=True).person
    except ApiToken.DoesNotExist:
        return None


def token_required(view):
    @wraps(view)
    @csrf_exempt
    def wrapped(request, *args, **kwargs):
        person = _person(request)
        if person is None:
            return JsonResponse({"error": "A valid API token is required."}, status=401)
        request.person = person
        try:
            return view(request, *args, **kwargs)
        except Refused as e:
            return JsonResponse({"error": str(e)}, status=400)

    return wrapped


def _body(request):
    try:
        return json.loads(request.body or b"{}")
    except ValueError:
        raise Refused("The request body must be JSON.")


def _sheet(request, code):
    try:
        sheet = Greensheet.objects.get(code=code)
    except Greensheet.DoesNotExist:
        raise Http404
    role = sheet.role_for(request.person)
    if role is None:
        raise Http404
    return sheet, role


def item_json(i):
    return {
        "number": i.number,
        "title": i.title,
        "note": i.note,
        "due_date": i.due_date.isoformat() if i.due_date else None,
        "complete": i.complete,
        "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        "completed_by": i.completed_by.display if i.completed_by else None,
        "overdue": i.overdue,
    }


def sheet_json(s, role, with_items=True):
    d = {
        "code": s.code,
        "name": s.name,
        "url": s.absolute_url,
        "your_role": role,
        "requester": {"name": s.requester.display, "email": s.requester.email},
        "fulfiller": {"name": s.fulfiller.display, "email": s.fulfiller.email},
        "contact": {"email": s.contact_email, "phone": s.contact_phone},
        "archived": s.archived,
        "created_at": s.created_at.isoformat(),
        "flip_of": s.flip_of.code if s.flip_of_id else None,
        "flip_side": (s.paired.code if (s.paired and not s.is_flip_side) else None),
    }
    if with_items:
        d["items"] = [item_json(i) for i in s.items.all()]
    return d


@token_required
@require_http_methods(["GET"])
def sheets(request):
    me = request.person
    out = [sheet_json(s, "requester", False) for s in Greensheet.objects.filter(requester=me)]
    out += [sheet_json(s, "fulfiller", False) for s in Greensheet.objects.filter(fulfiller=me)]
    return JsonResponse({"greensheets": out})


@token_required
@require_http_methods(["GET"])
def sheet(request, code):
    s, role = _sheet(request, code)
    return JsonResponse(sheet_json(s, role))


@token_required
@require_http_methods(["POST"])
def add_item(request, code):
    s, role = _sheet(request, code)
    if role != "requester":
        return JsonResponse({"error": "Only the requester can add items."}, status=403)
    b = _body(request)
    from .views import _parse_date

    item = services.add_item(
        s, request.person, title=b.get("title", ""), note=b.get("note", ""), due_date=_parse_date(b.get("due_date"))
    )
    return JsonResponse(item_json(item), status=201)


@token_required
@require_http_methods(["POST"])
def complete(request, code, number):
    s, role = _sheet(request, code)
    item = s.items.filter(number=number).first()
    if item is None:
        raise Http404
    services.complete_item(item, request.person)
    return JsonResponse(item_json(item))


@token_required
@require_http_methods(["POST"])
def reopen(request, code, number):
    s, role = _sheet(request, code)
    item = s.items.filter(number=number).first()
    if item is None:
        raise Http404
    services.reopen_item(item, request.person)
    return JsonResponse(item_json(item))


@token_required
@require_http_methods(["GET"])
def events(request, code):
    s, role = _sheet(request, code)
    out = [
        {"at": e.at.isoformat(), "kind": e.kind, "actor": e.actor_name, "data": e.data, "description": e.description}
        for e in s.events.order_by("at", "id")
    ]
    return JsonResponse({"events": out})


urlpatterns = [
    path("sheets", sheets),
    path("sheets/<str:code>", sheet),
    path("sheets/<str:code>/items", add_item),
    path("sheets/<str:code>/items/<int:number>/complete", complete),
    path("sheets/<str:code>/items/<int:number>/reopen", reopen),
    path("sheets/<str:code>/events", events),
]
