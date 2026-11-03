from django import forms
from django.contrib import admin, messages

from .models import Client, ClientDomain
from .provisioning import provision


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = "__all__"  # noqa: DJ007 - ClientAdmin.fieldsets decides what is shown


class ClientDomainInline(admin.TabularInline):
    model = ClientDomain
    extra = 1


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    form = ClientForm
    inlines = [ClientDomainInline]
    list_display = ("name", "slug", "status", "db_strategy", "db_name", "updated_at")
    list_filter = ("status", "db_strategy")
    search_fields = ("name", "slug", "domains__domain")
    readonly_fields = ("created_at", "updated_at")
    actions = ["provision_selected"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "status")}),
        ("Database", {"fields": ("db_strategy", "db_name", "db_params")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append("slug")
        return ro

    @admin.action(description="Provision database (create + migrate + activate)")
    def provision_selected(self, request, queryset):
        for client in queryset:
            try:
                provision(client)
                self.message_user(request, f"Provisioned {client}.", messages.SUCCESS)
            except Exception as exc:  # noqa: BLE001
                self.message_user(request, f"{client}: {exc}", messages.ERROR)
