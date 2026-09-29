"""
Run with: python manage.py test
"""

import json
from datetime import date, timedelta
from unittest import mock

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import services
from .models import Block, DigestSubscription, Event, Greensheet, Item, Person, Webhook


def signin(person):
    c = Client()
    link = services.issue_magic_link(person, "/", send=False)
    r = c.get(f"/auth/{link.token}")
    assert r.status_code == 302, r.status_code
    return c


class Base(TestCase):
    def setUp(self):
        self.dana, _ = Person.objects.get_or_create_by_email("dana@example.com", "Dana Whitfield")
        self.sheet = services.create_greensheet(
            self.dana,
            name="2025 tax engagement",
            fulfiller_email="marcus@example.com",
            fulfiller_name="Marcus Bell",
            contact_phone="(573) 555-0142",
        )
        self.marcus = self.sheet.fulfiller
        self.i1 = services.add_item(self.sheet, self.dana, title="Sign the engagement letter", due_date=date(2026, 10, 3))
        self.i2 = services.add_item(self.sheet, self.dana, title="Provide tax returns", note="See https://example.com/x")
        mail.outbox.clear()


class SignInTests(Base):
    def test_magic_link_is_single_use_and_signs_in(self):
        link = services.issue_magic_link(self.marcus, "/", send=False)
        c = Client()
        self.assertEqual(c.get(f"/auth/{link.token}").status_code, 302)
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(Client().get(f"/auth/{link.token}").status_code, 410)

    def test_signin_form_creates_person_and_sends_link(self):
        r = Client().post("/signin", {"email": "New@Example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Person.objects.filter(email="new@example.com").exists())
        self.assertEqual(mail.outbox[-1].subject, "Greensheet: sign in")

    def test_rate_limit(self):
        from .models import MagicLink

        with self.assertRaises(services.Refused):
            for _ in range(6):
                services.issue_magic_link(self.marcus, "/", send=False)
        self.assertEqual(MagicLink.objects.filter(person=self.marcus).count(), 5)

    @override_settings(ALLOWLIST=["example.org", "vip@example.com"])
    def test_allowlist_blocks_strangers_but_not_invited(self):
        self.assertFalse(services.cold_signin_allowed("nobody@example.com"))
        self.assertTrue(services.cold_signin_allowed("anyone@example.org"))
        self.assertTrue(services.cold_signin_allowed("vip@example.com"))
        self.assertTrue(services.cold_signin_allowed("marcus@example.com"))  # invited
        r = Client().post("/signin", {"email": "nobody@example.com"})
        self.assertContains(r, "by invitation")

    def test_revoke_signs_out_everywhere(self):
        m = signin(self.marcus)
        self.assertEqual(m.get(f"/s/{self.sheet.code}").status_code, 200)
        d = signin(self.dana)
        d.post(f"/s/{self.sheet.code}/revoke")
        self.assertContains(m.get(f"/s/{self.sheet.code}"), "Sign in to open this greensheet")
        self.assertTrue(Event.objects.filter(kind="session.revoked").exists())
        # and can sign back in
        m2 = signin(self.marcus)
        self.assertEqual(m2.get(f"/s/{self.sheet.code}").status_code, 200)


class GreensheetTests(Base):
    def test_fulfiller_sees_sheet_and_cannot_add(self):
        m = signin(self.marcus)
        r = m.get(f"/s/{self.sheet.code}")
        self.assertContains(r, "2025 tax engagement · Greensheet")
        self.assertContains(r, "mailto:dana@example.com")
        self.assertContains(r, "sms:5735550142")
        self.assertContains(r, "Scan to open")
        self.assertNotContains(r, "Add an item")
        self.assertEqual(m.post(f"/s/{self.sheet.code}/items", {"title": "x"}).status_code, 404)

    def test_stranger_gets_404(self):
        s = signin(Person.objects.get_or_create_by_email("stranger@example.com")[0])
        self.assertEqual(s.get(f"/s/{self.sheet.code}").status_code, 404)

    def test_complete_reopen_htmx_and_plain(self):
        m = signin(self.marcus)
        r = m.post(f"/s/{self.sheet.code}/items/1/complete", HTTP_HX_REQUEST="true")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'class="item done')
        self.assertTrue(Item.objects.get(pk=self.i1.pk).complete)
        r = m.post(f"/s/{self.sheet.code}/items/1/reopen")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Item.objects.get(pk=self.i1.pk).complete)
        kinds = list(Event.objects.filter(greensheet=self.sheet).order_by("at", "id").values_list("kind", flat=True))
        self.assertEqual(kinds[-2:], ["item.completed", "item.reopened"])

    def test_requester_crud_and_item_numbers_never_reuse(self):
        d = signin(self.dana)
        d.post(f"/s/{self.sheet.code}/items", {"title": "Third", "due_date": "2026-10-15"})
        self.assertEqual(Item.objects.get(greensheet=self.sheet, number=3).due_date, date(2026, 10, 15))
        d.post(f"/s/{self.sheet.code}/items/3/edit", {"title": "Third edited", "note": "", "due_date": ""})
        it = Item.objects.get(greensheet=self.sheet, number=3)
        self.assertEqual(it.title, "Third edited")
        self.assertIsNone(it.due_date)
        d.post(f"/s/{self.sheet.code}/items/3/delete")
        self.assertFalse(Item.objects.filter(greensheet=self.sheet, number=3).exists())
        d.post(f"/s/{self.sheet.code}/items", {"title": "Fourth"})
        self.assertTrue(Item.objects.filter(greensheet=self.sheet, number=4).exists())

    def test_archive_is_read_only_for_both(self):
        d = signin(self.dana)
        d.post(f"/s/{self.sheet.code}/archive")
        self.sheet.refresh_from_db()
        self.assertTrue(self.sheet.archived)
        m = signin(self.marcus)
        self.assertEqual(m.post(f"/s/{self.sheet.code}/items/1/complete").status_code, 400)
        self.assertEqual(m.get(f"/s/{self.sheet.code}").status_code, 200)
        d.post(f"/s/{self.sheet.code}/unarchive")
        self.sheet.refresh_from_db()
        self.assertFalse(self.sheet.archived)

    def test_completed_hidden_by_default(self):
        services.complete_item(self.i2, self.marcus)
        m = signin(self.marcus)
        self.assertNotContains(m.get(f"/s/{self.sheet.code}"), "Provide tax returns")
        m.get(f"/s/{self.sheet.code}?completed=show")
        self.assertContains(m.get(f"/s/{self.sheet.code}"), "Provide tax returns")
        m.get(f"/s/{self.sheet.code}?completed=hide")
        self.assertNotContains(m.get(f"/s/{self.sheet.code}"), "Provide tax returns")

    def test_completing_over_htmx_marks_the_row_as_leaving_and_updates_counts(self):
        m = signin(self.marcus)
        r = m.post(f"/s/{self.sheet.code}/items/1/complete", HTTP_HX_REQUEST="true")
        self.assertContains(r, 'class="item done leaving"')
        self.assertContains(r, "2 items · 1 complete")
        self.assertContains(r, "Show completed")
        m.get(f"/s/{self.sheet.code}?completed=show")
        r = m.post(f"/s/{self.sheet.code}/items/2/complete", HTTP_HX_REQUEST="true")
        self.assertContains(r, 'class="item done"')

    def test_page_shows_the_address_the_browser_used_unless_site_url_is_set(self):
        m = signin(self.marcus)
        r = m.get(f"/s/{self.sheet.code}", HTTP_HOST="127.0.0.1:8765")
        with override_settings(SITE_URL_EXPLICIT=False):
            r = m.get(f"/s/{self.sheet.code}", HTTP_HOST="127.0.0.1:8765")
            self.assertContains(r, f"127.0.0.1:8765/s/{self.sheet.code}")
        with override_settings(SITE_URL_EXPLICIT=True, SITE_URL="https://example.org"):
            r = m.get(f"/s/{self.sheet.code}", HTTP_HOST="127.0.0.1:8765")
            self.assertContains(r, f"example.org/s/{self.sheet.code}")

    def test_history_page(self):
        services.complete_item(self.i1, self.marcus)
        r = signin(self.dana).get(f"/s/{self.sheet.code}/history")
        self.assertContains(r, "Marcus Bell completed item 1")


class ChannelTests(Base):
    def test_fulfiller_links_carry_compose_data_and_mobile_only_marks(self):
        r = signin(self.marcus).get(f"/s/{self.sheet.code}")
        self.assertContains(r, 'class="ch-email" href="mailto:dana@example.com')
        self.assertContains(r, 'data-subject="Greensheet: 2025 tax engagement, item 1"')
        self.assertContains(r, 'class="mobile-only" href="sms:5735550142')
        self.assertContains(r, 'class="mobile-only" href="tel:5735550142')
        self.assertContains(r, "channels.js")


class RequesterViewTests(Base):
    def test_requester_sees_no_channel_links(self):
        r = signin(self.dana).get(f"/s/{self.sheet.code}")
        self.assertNotContains(r, "mailto:")
        self.assertContains(r, "Preview as Marcus Bell")

    def test_requester_add_partial_has_no_channels(self):
        d = signin(self.dana)
        r = d.post(f"/s/{self.sheet.code}/items/1/reopen", HTTP_HX_REQUEST="true")
        self.assertNotContains(r, "mailto:")

    def test_preview_renders_fulfiller_view_read_only(self):
        r = signin(self.dana).get(f"/s/{self.sheet.code}?preview=1")
        self.assertContains(r, "Previewing as Marcus Bell")
        self.assertContains(r, "mailto:dana@example.com")
        self.assertNotContains(r, "Add an item")
        self.assertNotContains(r, 'class="corner')
        self.assertContains(r, 'class="box static"')

    def test_preview_ignored_for_fulfiller(self):
        r = signin(self.marcus).get(f"/s/{self.sheet.code}?preview=1")
        self.assertNotContains(r, "Previewing as")

    def test_home_wording_and_hidden_form(self):
        r = signin(self.dana).get("/")
        self.assertContains(r, ">For you<")
        self.assertContains(r, ">From you<")
        self.assertNotContains(r, "Set by you")
        self.assertContains(r, "2 open")  # two items on the sheet Dana set for Marcus
        self.assertContains(r, 'id="create-form" hidden')
        self.assertContains(signin(self.marcus).get("/"), "2 to do")


class InviteTests(Base):
    def test_invite_email_grammar_and_decline_blocks(self):
        sheet = services.create_greensheet(self.dana, name="Kitchen", fulfiller_email="pat@example.com")
        self.assertEqual(mail.outbox[-1].subject, "Greensheet: Kitchen from Dana Whitfield")
        self.assertIn(sheet.absolute_url, mail.outbox[-1].body)
        self.assertNotIn("/auth/", mail.outbox[-1].body, "the invite is the greensheet's address, not a magic link")
        r = Client().get(f"/invite/{sheet.invite.token}/decline")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Block.objects.filter(requester=self.dana, person__email="pat@example.com").exists())
        with self.assertRaises(services.Refused):
            services.create_greensheet(self.dana, name="Again", fulfiller_email="pat@example.com")

    def test_sheet_link_asks_signed_out_visitor_to_sign_in_then_returns(self):
        from .models import MagicLink

        c = Client()
        url = self.sheet.get_absolute_url()
        r = c.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sign in to open this greensheet")
        # The destination rides in a hidden field, never the query string:
        # a POST to /signin?next=/s/... is blocked by common proxy firewalls.
        self.assertContains(r, 'action="/signin"')
        self.assertContains(r, f'name="next" value="{url}"')
        r = c.post("/signin", {"email": self.marcus.email, "next": url})
        self.assertEqual(r.status_code, 200)
        link = MagicLink.objects.filter(person=self.marcus).latest("created_at")
        self.assertEqual(link.next, url)
        self.assertRedirects(c.get(f"/auth/{link.token}"), url, fetch_redirect_response=False)
        self.assertContains(c.get(url), self.sheet.name)
        self.assertTrue(Greensheet.objects.get(pk=self.sheet.pk).invite.accepted_at)
        # Signed in, the same address opens the greensheet; sign-in with next just goes there.
        self.assertRedirects(c.get(f"/signin?next={url}"), url, fetch_redirect_response=False)
        # A stale link points back at the greensheet, not the generic sign-in page.
        self.assertContains(Client().get(f"/auth/{link.token}"), f'href="{url}"', status_code=410)

    def test_cannot_set_greensheet_for_self(self):
        with self.assertRaises(services.Refused):
            services.create_greensheet(self.dana, name="Me", fulfiller_email=self.dana.email)


class FlipSideTests(Base):
    def test_only_fulfiller_sees_corner_before_creation(self):
        self.assertContains(signin(self.marcus).get(f"/s/{self.sheet.code}"), 'class="corner')
        self.assertNotContains(signin(self.dana).get(f"/s/{self.sheet.code}"), 'class="corner')

    def test_explain_then_create(self):
        m = signin(self.marcus)
        r = m.get(f"/s/{self.sheet.code}/flip")
        self.assertContains(r, "A greensheet has two faces")
        r = m.post(f"/s/{self.sheet.code}/flip")
        flip = Greensheet.objects.get(flip_of=self.sheet)
        self.assertRedirects(r, flip.get_absolute_url() + "?flipped=1", fetch_redirect_response=False)
        self.assertEqual(flip.requester, self.marcus)
        self.assertEqual(flip.fulfiller, self.dana)
        self.assertEqual(flip.name, "Flip side of 2025 tax engagement")
        self.assertEqual(flip.contact_email, self.marcus.email)
        self.assertTrue(flip.invite.accepted_at)
        self.assertEqual(len(mail.outbox), 0, "no invite email for the flip side")
        self.assertTrue(Event.objects.filter(kind="flip.created", greensheet=self.sheet).exists())

    def test_roles_reverse_on_flip_side(self):
        flip = services.create_flip_side(self.sheet, self.marcus)
        m = signin(self.marcus)
        r = m.get(flip.get_absolute_url())
        self.assertContains(r, "Add an item")
        self.assertContains(r, "flip side of 2025 tax engagement")
        m.post(f"/s/{flip.code}/items", {"title": "Send me the invoice"})
        d = signin(self.dana)
        r = d.get(flip.get_absolute_url())
        self.assertNotContains(r, "Add an item")
        r = d.post(f"/s/{flip.code}/items/1/complete", HTTP_HX_REQUEST="true")
        self.assertContains(r, 'class="item done')

    def test_corner_links_both_ways_once_created(self):
        flip = services.create_flip_side(self.sheet, self.marcus)
        d = signin(self.dana)
        self.assertContains(d.get(f"/s/{self.sheet.code}"), 'class="corner')
        r = d.get(f"/s/{self.sheet.code}/flip")
        self.assertRedirects(r, flip.get_absolute_url() + "?flipped=1", fetch_redirect_response=False)
        r = d.get(f"/s/{flip.code}/flip")
        self.assertRedirects(r, self.sheet.get_absolute_url() + "?flipped=1", fetch_redirect_response=False)

    def test_only_fulfiller_can_create_and_only_once(self):
        with self.assertRaises(services.Refused):
            services.create_flip_side(self.sheet, self.dana)
        self.assertEqual(signin(self.dana).get(f"/s/{self.sheet.code}/flip").status_code, 404)
        flip = services.create_flip_side(self.sheet, self.marcus)
        self.assertEqual(services.create_flip_side(self.sheet, self.marcus), flip)
        with self.assertRaises(services.Refused):
            services.create_flip_side(flip, self.dana)

    def test_home_labels_flip_sides(self):
        services.create_flip_side(self.sheet, self.marcus)
        self.assertContains(signin(self.dana).get("/"), "flip side")

    def test_api_exposes_pairing(self):
        flip = services.create_flip_side(self.sheet, self.marcus)
        tok = services.create_token(self.dana)
        a = Client(HTTP_AUTHORIZATION=f"Bearer {tok.key}")
        self.assertEqual(a.get(f"/api/sheets/{self.sheet.code}").json()["flip_side"], flip.code)
        self.assertEqual(a.get(f"/api/sheets/{flip.code}").json()["flip_of"], self.sheet.code)


class DigestTests(Base):
    def test_compose_for_each_role(self):
        services.complete_item(self.i1, self.marcus)
        sub = services.digest_for(self.sheet, self.dana)
        subject, body = services.compose_digest(sub)
        self.assertEqual(subject, "Greensheet: 2025 tax engagement, 1 completed")
        self.assertIn("Sign the engagement letter", body)
        sub2 = services.digest_for(self.sheet, self.marcus)
        subject2, body2 = services.compose_digest(sub2)
        self.assertTrue(subject2.startswith("Greensheet: 2025 tax engagement, 2 new"))
        self.assertIn("Stop:", body2)

    def test_nothing_to_say(self):
        sub = services.digest_for(self.sheet, self.dana)
        self.assertIsNone(services.compose_digest(sub))

    def test_toggle_and_off_link(self):
        m = signin(self.marcus)
        m.post(f"/s/{self.sheet.code}/summary")
        self.assertTrue(DigestSubscription.objects.get(greensheet=self.sheet, person=self.marcus).enabled)
        m.get(f"/s/{self.sheet.code}/summary/off")
        self.assertFalse(DigestSubscription.objects.get(greensheet=self.sheet, person=self.marcus).enabled)


class ApiTests(Base):
    def test_token_flow(self):
        tok = services.create_token(self.dana, "t")
        a = Client(HTTP_AUTHORIZATION=f"Bearer {tok.key}")
        self.assertEqual(a.get("/api/sheets").json()["greensheets"][0]["code"], self.sheet.code)
        r = a.post(f"/api/sheets/{self.sheet.code}/items", data=json.dumps({"title": "Via API", "due_date": "2026-11-01"}), content_type="application/json")
        self.assertEqual(r.status_code, 201)
        n = r.json()["number"]
        self.assertTrue(a.post(f"/api/sheets/{self.sheet.code}/items/{n}/complete").json()["complete"])
        self.assertTrue(any(e["kind"] == "item.completed" for e in a.get(f"/api/sheets/{self.sheet.code}/events").json()["events"]))
        self.assertEqual(Client().get("/api/sheets").status_code, 401)

    def test_fulfiller_token_cannot_add(self):
        tok = services.create_token(self.marcus)
        a = Client(HTTP_AUTHORIZATION=f"Bearer {tok.key}")
        r = a.post(f"/api/sheets/{self.sheet.code}/items", data='{"title":"x"}', content_type="application/json")
        self.assertEqual(r.status_code, 403)


@override_settings(WEBHOOK_SYNC=True)
class WebhookTests(Base):
    def test_delivery_signed_and_recorded(self):
        hook = services.create_webhook(self.dana, "https://example.com/hook", "test")
        captured = {}

        class Resp:
            status = 204

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.headers)
            captured["body"] = req.data
            return Resp()

        with mock.patch("sheets.webhooks.urllib.request.urlopen", fake_urlopen):
            with self.captureOnCommitCallbacks(execute=True):
                services.complete_item(self.i1, self.marcus)
        self.assertEqual(captured["url"], "https://example.com/hook")
        body = json.loads(captured["body"])
        self.assertEqual(body["kind"], "item.completed")
        self.assertEqual(body["item"]["number"], 1)
        self.assertEqual(body["greensheet"]["code"], self.sheet.code)
        import hashlib, hmac

        expect = hmac.new(hook.secret.encode(), captured["body"], hashlib.sha256).hexdigest()
        self.assertEqual(captured["headers"]["X-greensheet-signature"], expect)
        hook.refresh_from_db()
        self.assertEqual(hook.last_status, 204)

    def test_failure_is_recorded_not_raised(self):
        hook = services.create_webhook(self.marcus, "http://127.0.0.1:1/nothing")
        with self.captureOnCommitCallbacks(execute=True):
            services.complete_item(self.i1, self.marcus)
        hook.refresh_from_db()
        self.assertIsNone(hook.last_status)
        self.assertTrue(hook.last_error)

    def test_bad_scheme_refused(self):
        with self.assertRaises(services.Refused):
            services.create_webhook(self.dana, "ftp://x")

    def test_page(self):
        d = signin(self.dana)
        d.post("/me/webhooks", {"url": "https://example.com/h", "label": "L"})
        self.assertContains(d.get("/me/webhooks"), "https://example.com/h")
        hook = Webhook.objects.get(person=self.dana)
        d.post("/me/webhooks", {"delete": hook.id})
        self.assertFalse(Webhook.objects.filter(pk=hook.pk).exists())


class DeletionTests(Base):
    def test_delete_fulfiller_leaves_placeholder(self):
        m = signin(self.marcus)
        r = m.post("/me/delete", {"confirm": self.marcus.email})
        self.assertEqual(r.status_code, 200)
        self.sheet.refresh_from_db()
        self.assertTrue(self.sheet.fulfiller.is_placeholder)
        self.assertFalse(Person.objects.filter(email="marcus@example.com").exists())
        self.assertTrue(Event.objects.filter(kind="person.deleted").exists())

    def test_delete_requester_removes_sheets_keeps_events(self):
        d = signin(self.dana)
        d.post("/me/delete", {"confirm": self.dana.email})
        self.assertFalse(Greensheet.objects.filter(pk=self.sheet.pk).exists())
        self.assertTrue(Event.objects.filter(kind="sheet.deleted", data__sheet_name="2025 tax engagement").exists())


class QualityOfLifeTests(Base):
    def test_icon_on_tab_and_rows_and_flip_side(self):
        d = signin(self.dana)
        d.post(f"/s/{self.sheet.code}/edit", {"name": self.sheet.name, "contact_email": self.dana.email, "contact_phone": "", "icon": " § "})
        self.sheet.refresh_from_db()
        self.assertEqual(self.sheet.icon, "§")
        r = d.get(f"/s/{self.sheet.code}")
        self.assertContains(r, 'rel="icon" href="data:image/svg+xml')
        self.assertContains(r, 'class="mark  has-glyph"')
        self.assertContains(d.get("/"), 'class="mark sm has-glyph"')
        self.assertEqual(Event.objects.filter(kind="sheet.edited").latest("at").data["changed"]["icon"], ["", "§"])
        m = signin(self.marcus)
        m.post(f"/s/{self.sheet.code}/flip")
        self.assertEqual(Greensheet.objects.get(flip_of=self.sheet).icon, "§")
        # plain mark without one
        self.assertContains(Client().get("/signin"), 'href="/static/mark.svg"')

    def test_icon_from_create_form_is_cleaned(self):
        d = signin(self.dana)
        d.post("/new", {"name": "Kitchen", "fulfiller_email": "pat@example.com", "icon": "🍳 extra long paste here"})
        self.assertEqual(Greensheet.objects.get(name="Kitchen").icon, "🍳 extra long pas")  # 16 code points

    def test_edit_item_in_place(self):
        d = signin(self.dana)
        r = d.get(f"/s/{self.sheet.code}/items/1/edit", HTTP_HX_REQUEST="true")
        self.assertContains(r, 'class="item editing"')
        self.assertContains(r, 'value="Sign the engagement letter"')
        r = d.post(f"/s/{self.sheet.code}/items/1/edit", {"title": "Sign it", "note": "", "due_date": ""}, HTTP_HX_REQUEST="true")
        self.assertContains(r, 'id="item-1"')
        self.assertContains(r, "Sign it")
        self.assertNotContains(r, 'class="item editing"')
        r = d.get(f"/s/{self.sheet.code}/items/1", HTTP_HX_REQUEST="true")
        self.assertContains(r, 'id="item-1"')
        # the same URLs are ordinary pages without htmx
        self.assertContains(d.get(f"/s/{self.sheet.code}/items/1/edit"), "<h1>Item 1</h1>")
        self.assertRedirects(d.get(f"/s/{self.sheet.code}/items/1"), self.sheet.get_absolute_url(), fetch_redirect_response=False)

    def test_new_tag_for_items_added_since_the_fulfillers_last_visit(self):
        from .models import Visit

        m = signin(self.marcus)
        self.assertNotContains(m.get(f"/s/{self.sheet.code}"), ">new<")  # first visit: nothing is new
        services.add_item(self.sheet, self.dana, title="Bring the receipts")
        r = m.get(f"/s/{self.sheet.code}")
        self.assertContains(r, ">new<", count=1)
        self.assertContains(r, "Bring the receipts")
        # a refresh within the visit keeps the tag
        self.assertContains(m.get(f"/s/{self.sheet.code}"), ">new<", count=1)
        # a later visit starts a fresh baseline: the old items predate it, the new one does not
        Item.objects.filter(greensheet=self.sheet).exclude(title="Bring the receipts").update(created_at=timezone.now() - timedelta(minutes=20))
        Visit.objects.filter(person=self.marcus).update(seen_at=timezone.now() - timedelta(minutes=11))
        self.assertContains(m.get(f"/s/{self.sheet.code}"), ">new<", count=1)  # still new: added after that baseline
        self.assertNotContains(m.get(f"/s/{self.sheet.code}"), ">new<")  # seen now
        # the requester never sees it
        services.add_item(self.sheet, self.dana, title="One more")
        self.assertNotContains(signin(self.dana).get(f"/s/{self.sheet.code}"), ">new<")

    def test_undo_line_after_a_row_leaves(self):
        m = signin(self.marcus)
        r = m.post(f"/s/{self.sheet.code}/items/1/complete", HTTP_HX_REQUEST="true")
        self.assertContains(r, 'id="undo" hx-swap-oob="true">Item 1 done.')
        self.assertContains(r, f'action="/s/{self.sheet.code}/items/1/reopen"')
        r = m.post(f"/s/{self.sheet.code}/items/1/reopen")
        self.assertRedirects(r, self.sheet.get_absolute_url(), fetch_redirect_response=False)
        self.assertContains(m.get(f"/s/{self.sheet.code}"), "Sign the engagement letter")

    def test_home_screen_manifest_and_icons(self):
        r = Client().get("/signin")
        self.assertContains(r, 'rel="manifest" href="/static/manifest.webmanifest"')
        self.assertContains(r, 'rel="apple-touch-icon" href="/static/icon-180.png"')
        from django.conf import settings

        for name in ("manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png", "icon-512-maskable.png"):
            self.assertTrue((settings.BASE_DIR / "static" / name).exists(), name)

    def test_start_from_an_existing_greensheet(self):
        # The source started ten days ago; item 1 was due seven days after that.
        Greensheet.objects.filter(pk=self.sheet.pk).update(created_at=timezone.now() - timedelta(days=10), icon="★")
        self.sheet.refresh_from_db()
        self.i1.due_date = timezone.localdate() - timedelta(days=3)
        self.i1.save()
        services.complete_item(self.i2, self.marcus)
        d = signin(self.dana)
        r = d.get(f"/?from={self.sheet.code}")
        self.assertContains(r, f'value="{self.sheet.code}" selected')
        d.post("/new", {"name": "Onboarding, Pat", "fulfiller_email": "pat@example.com", "copy_from": self.sheet.code})
        new = Greensheet.objects.get(name="Onboarding, Pat")
        titles = list(new.items.values_list("title", flat=True))
        self.assertEqual(titles, ["Sign the engagement letter", "Provide tax returns"])
        self.assertEqual(new.items.get(number=1).due_date, timezone.localdate() + timedelta(days=7))
        self.assertIsNone(new.items.get(number=2).due_date)
        self.assertFalse(new.items.get(number=2).complete, "completion does not copy")
        self.assertEqual(new.items.get(number=2).note, "See https://example.com/x")
        self.assertEqual(new.icon, "★")
        self.assertEqual(Event.objects.get(kind="sheet.created", greensheet=new).data["copied_from"], self.sheet.code)
        self.assertContains(d.get(f"/s/{new.code}/history"), "starting from another")
        # only your own greensheets are a starting point
        m = signin(self.marcus)
        r = m.post("/new", {"name": "Nope", "fulfiller_email": "x@example.com", "copy_from": self.sheet.code})
        self.assertEqual(r.status_code, 404)
        self.assertContains(d.get(f"/s/{self.sheet.code}"), "Set this for someone else")


class DraftTests(Base):
    def test_draft_is_private_unsent_and_can_be_sent_later(self):
        d = signin(self.dana)
        d.post("/new", {"name": "Onboarding", "fulfiller_email": "typed@example.com", "draft": "1"})
        draft = Greensheet.objects.get(name="Onboarding")
        self.assertTrue(draft.is_draft)
        self.assertIsNone(draft.fulfiller)
        self.assertEqual(len(mail.outbox), 0, "a draft sends nothing")
        self.assertFalse(Person.objects.filter(email="typed@example.com").exists(), "save as draft ignores the email box")
        self.assertEqual(Event.objects.get(kind="sheet.created", greensheet=draft).data["draft"], True)
        r = d.get(f"/s/{draft.code}")
        self.assertContains(r, "not sent to anyone yet")
        self.assertContains(r, "Send it when it is ready")
        self.assertNotContains(r, "Preview as")
        self.assertNotContains(r, "Daily summary")
        self.assertContains(d.get("/"), "not sent yet")
        self.assertNotContains(d.get(f"/s/{draft.code}/edit"), "out everywhere")
        # nobody else can see it
        self.assertEqual(signin(self.marcus).get(f"/s/{draft.code}").status_code, 404)
        # items go on it like any greensheet
        services.add_item(draft, self.dana, title="Laptop and badge")
        # sending it
        r = d.post(f"/s/{draft.code}/send", {"fulfiller_email": "Pat@Example.com", "fulfiller_name": "Pat Lee"})
        self.assertRedirects(r, draft.get_absolute_url(), fetch_redirect_response=False)
        draft.refresh_from_db()
        self.assertFalse(draft.is_draft)
        self.assertEqual(draft.fulfiller.email, "pat@example.com")
        self.assertEqual(mail.outbox[-1].subject, "Greensheet: Onboarding from Dana Whitfield")
        self.assertIn(draft.absolute_url, mail.outbox[-1].body)
        self.assertTrue(draft.invite.pk)
        self.assertContains(d.get(f"/s/{draft.code}/history"), "sent the greensheet to pat@example.com")
        self.assertNotContains(d.get(f"/s/{draft.code}"), "Send it when it is ready")
        # Pat can open it now
        pat = Person.objects.get(email="pat@example.com")
        self.assertContains(signin(pat).get(f"/s/{draft.code}"), "Laptop and badge")

    def test_blank_email_on_the_create_form_also_makes_a_draft(self):
        d = signin(self.dana)
        d.post("/new", {"name": "Someday", "fulfiller_email": ""})
        self.assertTrue(Greensheet.objects.get(name="Someday").is_draft)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_refuses_self_blocked_and_already_sent(self):
        d = signin(self.dana)
        d.post("/new", {"name": "Draft", "draft": "1"})
        draft = Greensheet.objects.get(name="Draft")
        with self.assertRaises(services.Refused):
            services.send_greensheet(draft, self.dana, fulfiller_email=self.dana.email)
        with self.assertRaises(services.Refused):
            services.send_greensheet(self.sheet, self.dana, fulfiller_email="x@example.com")
        with self.assertRaises(services.Refused):
            services.send_greensheet(draft, self.marcus, fulfiller_email="x@example.com")
        with self.assertRaises(services.Refused):
            services.create_flip_side(draft, self.dana)

    def test_draft_as_a_starting_point_and_in_the_api(self):
        d = signin(self.dana)
        d.post("/new", {"name": "Template", "draft": "1"})
        tpl = Greensheet.objects.get(name="Template")
        services.add_item(tpl, self.dana, title="Step one")
        d.post("/new", {"name": "For Sam", "fulfiller_email": "sam@example.com", "copy_from": tpl.code})
        new = Greensheet.objects.get(name="For Sam")
        self.assertFalse(new.is_draft)
        self.assertEqual(list(new.items.values_list("title", flat=True)), ["Step one"])
        token = services.create_token(self.dana, "t")
        r = Client().get("/api/sheets", HTTP_AUTHORIZATION=f"Bearer {token.key}")
        rows = {g["code"]: g for g in r.json()["greensheets"]}
        self.assertTrue(rows[tpl.code]["draft"])
        self.assertIsNone(rows[tpl.code]["fulfiller"])
        self.assertFalse(rows[new.code]["draft"])

