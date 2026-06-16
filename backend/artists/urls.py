from django.urls import path
from .views import update_page_builder, update_artist_profile, follow_artist, unfollow_artist, follow_stats, artist_list

urlpatterns = [
    path("", artist_list),

    path("follow/", follow_artist),
    path("unfollow/", unfollow_artist),
    path("follow-stats/", follow_stats),

    path("update-profile/", update_artist_profile),

    path("update-page-builder/", update_page_builder),
]
