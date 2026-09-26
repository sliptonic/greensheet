from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("signin", views.signin, name="signin"),
    path("signout", views.signout, name="signout"),
    path("auth/<str:token>", views.consume, name="consume"),
    path("invite/<str:token>/decline", views.decline, name="decline"),
    path("new", views.new_sheet, name="new_sheet"),
    path("me/tokens", views.tokens, name="tokens"),
    path("me/delete", views.delete_me, name="delete_me"),
    path("me/webhooks", views.webhooks, name="webhooks"),
    path("s/<str:code>/flip", views.flip, name="flip"),
    path("s/<str:code>/revoke", views.revoke, name="revoke"),
    path("s/<str:code>", views.sheet, name="sheet"),
    path("s/<str:code>/history", views.history, name="history"),
    path("s/<str:code>/edit", views.edit_sheet, name="edit_sheet"),
    path("s/<str:code>/archive", views.archive, name="archive"),
    path("s/<str:code>/unarchive", views.unarchive, name="unarchive"),
    path("s/<str:code>/summary", views.digest_toggle, name="digest_toggle"),
    path("s/<str:code>/summary/off", views.digest_off, name="digest_off"),
    path("s/<str:code>/items", views.add_item, name="add_item"),
    path("s/<str:code>/items/<int:number>/complete", views.complete, name="complete"),
    path("s/<str:code>/items/<int:number>/reopen", views.reopen, name="reopen"),
    path("s/<str:code>/items/<int:number>/edit", views.edit_item, name="edit_item"),
    path("s/<str:code>/items/<int:number>/delete", views.delete_item, name="delete_item"),
]
