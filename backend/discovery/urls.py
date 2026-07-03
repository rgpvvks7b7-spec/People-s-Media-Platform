from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('artists/', views.artist_recommendations),
    path('tracks/', views.track_recommendations),
    path('saved-artists/', views.saved_artists),
    path('signal/', views.record_artist_signal),
    path('track-signal/', views.record_track_signal),
    path('reset-skips/', views.reset_skipped_artists),
    path('undo-skip/', views.undo_skip_artist),
    path('undo-track-skip/', views.undo_track_skip),
    path('remove-saved/', views.remove_saved_artist),
    path('undo-signal/', views.undo_artist_signal),
    path('playing-near-you/', views.playing_near_you),
    path('my-scene/', views.my_scene),
    path('shows/<int:booking_id>/', views.show_detail),
    path('search/', views.global_search),
    path('featured/', views.featured_artists),
]
