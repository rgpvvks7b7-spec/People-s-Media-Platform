from django.contrib import admin

from .models import (
    MediaAbuseFlag,
    MediaAccessLog,
    PasskeyCredential,
    ReleaseApproval,
    WebAuthnChallenge,
)


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


@admin.register(MediaAccessLog)
class MediaAccessLogAdmin(admin.ModelAdmin):
    list_display = ("id", "access_type", "user", "artist", "content_type", "object_id", "ip_address", "created_at")
    list_filter = ("access_type", "content_type")
    search_fields = ("user__username", "artist__username", "ip_address", "user_agent")
    readonly_fields = (
        "user",
        "artist",
        "content_type",
        "object_id",
        "access_type",
        "ip_address",
        "user_agent",
        "created_at",
    )
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False


@admin.register(MediaAbuseFlag)
class MediaAbuseFlagAdmin(admin.ModelAdmin):
    list_display = ("id", "flag_type", "status", "user", "artist", "ip_address", "detail", "created_at")
    list_filter = ("flag_type", "status")
    search_fields = ("user__username", "artist__username", "ip_address", "detail")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
