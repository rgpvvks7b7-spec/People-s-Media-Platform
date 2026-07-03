import csv

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse

from .models import BetaFeedback, FanWaitlistEntry, User

admin.site.register(User, UserAdmin)


@admin.register(BetaFeedback)
class BetaFeedbackAdmin(admin.ModelAdmin):
    list_display = ("summary", "user", "category", "severity", "resolved", "created_at")
    list_filter = ("category", "severity", "resolved", "created_at")
    search_fields = ("summary", "details", "user__username", "user__display_name")


@admin.action(description="Export selected waitlist entries as CSV")
def export_waitlist_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="fan-waitlist.csv"'
    writer = csv.writer(response)
    writer.writerow(["email", "city", "favorite_genres", "source", "confirmed", "created_at"])
    for entry in queryset.order_by("created_at"):
        writer.writerow([
            entry.email,
            entry.city,
            entry.favorite_genres,
            entry.source,
            entry.confirmed,
            entry.created_at.isoformat(),
        ])
    return response


@admin.register(FanWaitlistEntry)
class FanWaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("email", "city", "confirmed", "source", "created_at")
    list_filter = ("confirmed", "source", "created_at")
    search_fields = ("email", "city", "favorite_genres")
    actions = [export_waitlist_csv]
