from django.urls import path

from . import views

urlpatterns = [
    path("", views.index),
    path("wallet/", views.wallet),
    path("wallet/redeem-preview/", views.redeem_preview),
    path("genres/", views.genres),
    path("targeting/suggestions/", views.targeting_suggestions),
    path("targeting/search/", views.targeting_search),
    path("campaigns/", views.campaigns),
    path("campaigns/<int:campaign_id>/action/", views.campaign_action),
    path("credits/checkout/", views.buy_credits),
    path("feedback/", views.feedback),
    path("share/", views.share_promoted),
    path("placements/", views.promotion_placements),
]
