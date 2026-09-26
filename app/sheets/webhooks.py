"""
Outbound bridges. Every event on a greensheet is POSTed, as JSON, to each
active webhook belonging to either party. The body is signed with the
webhook's secret: X-Greensheet-Signature is the hex HMAC-SHA256 of the body.

Delivery is best effort in a background thread. No retries. The last
status and error are kept on the webhook so the owner can see it working.
"""

import hashlib
import hmac
import json
import threading
import urllib.error
import urllib.request

from django.conf import settings
from django.db import connection
from django.utils import timezone


def payload(event):
    s = event.greensheet
    return {
        "id": event.id,
        "at": event.at.isoformat(),
        "kind": event.kind,
        "description": event.description,
        "actor": event.actor_name,
        "greensheet": {"code": s.code, "name": s.name, "url": s.absolute_url} if s else None,
        "item": {"number": event.data.get("item_number"), "title": event.data.get("item_title")}
        if event.data.get("item_number")
        else None,
        "data": event.data,
    }


def deliver(event):
    if not settings.WEBHOOKS_ENABLED or event.greensheet_id is None:
        return
    from .models import Webhook

    s = event.greensheet
    hooks = list(Webhook.objects.filter(active=True, person_id__in=[s.requester_id, s.fulfiller_id]))
    if not hooks:
        return
    body = json.dumps(payload(event)).encode()
    for h in hooks:
        args = (h.id, h.url, h.secret, body, event.kind)
        if settings.WEBHOOK_SYNC:
            _post(*args)
        else:
            threading.Thread(target=_post, args=args, daemon=True).start()


def _post(hook_id, url, secret, body, kind):
    from .models import Webhook

    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Greensheet",
            "X-Greensheet-Event": kind,
            "X-Greensheet-Signature": sig,
        },
    )
    status, err = None, ""
    try:
        with urllib.request.urlopen(req, timeout=settings.WEBHOOK_TIMEOUT) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status, err = e.code, str(e)[:200]
    except Exception as e:  # network errors, timeouts
        err = str(e)[:200]
    try:
        Webhook.objects.filter(id=hook_id).update(last_at=timezone.now(), last_status=status, last_error=err)
    finally:
        if not settings.WEBHOOK_SYNC:
            connection.close()
