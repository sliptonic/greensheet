from django.contrib import admin

from .models import ApiToken, Block, DigestSubscription, Event, Greensheet, Invite, Item, MagicLink, Person, Webhook


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "is_staff", "is_placeholder", "created_at")
    search_fields = ("email", "name")
    ordering = ("email",)


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0
    fields = ("number", "title", "due_date", "completed_at", "completed_by")
    readonly_fields = ("number",)


@admin.register(Greensheet)
class GreensheetAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "requester", "fulfiller", "flip_of", "created_at", "archived_at")
    search_fields = ("name", "code", "requester__email", "fulfiller__email")
    inlines = [ItemInline]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("at", "kind", "greensheet", "actor", "description")
    list_filter = ("kind",)
    date_hierarchy = "at"
    readonly_fields = ("at", "kind", "greensheet", "item", "actor", "data")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(Invite)
admin.site.register(Block)
admin.site.register(MagicLink)
admin.site.register(DigestSubscription)
admin.site.register(ApiToken)
admin.site.register(Webhook)
admin.site.site_header = "Greensheet operator"
admin.site.site_title = "Greensheet"
