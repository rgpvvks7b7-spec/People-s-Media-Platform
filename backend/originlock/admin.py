from django.contrib import admin

from .models import PasskeyCredential, ReleaseApproval, WebAuthnChallenge


@admin.register(ReleaseApproval)
class ReleaseApprovalAdmin(admin.ModelAdmin):
    list_display = ("id", "artist", "approval_status", "approval_method", "approved_at", "created_at")
    list_filter = ("approval_status", "approval_method")
    search_fields = ("artist__username", "rights_owner", "file_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "label", "created_at", "last_used_at")
    search_fields = ("user__username", "label")


admin.site.register(WebAuthnChallenge)
