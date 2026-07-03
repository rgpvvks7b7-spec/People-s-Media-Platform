from django.contrib import admin

from .models import Campaign, CampaignEvent, Genre, PromotionLedgerEntry


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "aliases")
    search_fields = ("name", "slug", "aliases")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "artist", "target_type", "target_id", "status", "budget", "spent", "discovery_score")
    list_filter = ("status", "target_type")
    search_fields = ("artist__username", "title")


@admin.register(CampaignEvent)
class CampaignEventAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "event_type", "fan", "charge", "created_at")
    list_filter = ("event_type",)


@admin.register(PromotionLedgerEntry)
class PromotionLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "entry_type", "amount", "balance_after", "campaign", "created_at")
    list_filter = ("entry_type",)
    search_fields = ("user__username",)
