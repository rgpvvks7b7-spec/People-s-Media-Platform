from django.contrib import admin

from .models import Campaign, CampaignMetrics


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "artist", "campaign_type", "goal", "status", "created_at")
    list_filter = ("status", "campaign_type", "goal")
    search_fields = ("title", "artist__username")


@admin.register(CampaignMetrics)
class CampaignMetricsAdmin(admin.ModelAdmin):
    list_display = ("campaign", "impressions", "clicks", "revenue", "updated_at")
