from django.urls import path
from artistcalendar.views import calendar_feed, calendar_item_detail, calendar_items
from .embed import public_artist_embed
from .fan_crm import fan_broadcast, fan_list
from .public import public_artist_meta
from .views import artist_dashboard, artist_pro_insights, artist_trust_status, fan_email_sharing, fans_also_support, mailing_list, record_page_view, update_page_builder, update_artist_profile, follow_artist, unfollow_artist, follow_stats, artist_list, stripe_connect_onboarding, stripe_connect_status

urlpatterns = [
    path("", artist_list),
    path("public/<str:username>/", public_artist_meta),
    path("public/<str:username>/embed/", public_artist_embed),
    path("calendar/", calendar_items),
    path("calendar/feed.ics", calendar_feed),
    path("calendar/<int:item_id>/", calendar_item_detail),

    path("follow/", follow_artist),
    path("unfollow/", unfollow_artist),
    path("fans-also-support/", fans_also_support),
    path("follow-stats/", follow_stats),
    path("mailing-list/", mailing_list),
    path("fans/", fan_list),
    path("fans/broadcast/", fan_broadcast),
    path("dashboard/", artist_dashboard),
    path("trust-status/", artist_trust_status),
    path("pro-insights/", artist_pro_insights),
    path("connect/status/", stripe_connect_status),
    path("connect/onboarding/", stripe_connect_onboarding),
    path("page-view/", record_page_view),
    path("fan-email-sharing/", fan_email_sharing),

    path("update-profile/", update_artist_profile),

    path("update-page-builder/", update_page_builder),
]
