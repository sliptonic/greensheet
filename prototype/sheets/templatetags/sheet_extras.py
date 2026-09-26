"""
Channels. A link channel is a URL that opens the external application with
the greensheet name and item number prefilled, so a conversation started
from the screen reads the same as one started from paper.
"""

from urllib.parse import quote

from django import template

register = template.Library()


def channels_for(sheet, item):
    subject = f"Greensheet: {sheet.name}, item {item.number}"
    body = f"About item {item.number}, {item.title}\n{sheet.absolute_url}\n\n"
    out = {"email": f"mailto:{sheet.contact_email}?subject={quote(subject)}&body={quote(body)}"}
    if sheet.contact_phone:
        digits = "".join(ch for ch in sheet.contact_phone if ch.isdigit() or ch == "+")
        out["sms"] = f"sms:{digits}?&body={quote(subject + '. ')}"
        out["tel"] = f"tel:{digits}"
    return out


@register.filter
def channel(sheet, item):
    return channels_for(sheet, item)


@register.filter
def get(d, key):
    return d.get(key, "")
