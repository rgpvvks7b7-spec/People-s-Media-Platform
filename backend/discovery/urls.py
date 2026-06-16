from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('artists/', views.artist_recommendations),
    path('saved-artists/', views.saved_artists),
    path('signal/', views.record_artist_signal),
    path('reset-skips/', views.reset_skipped_artists),
    path('undo-skip/', views.undo_skip_artist),
    path('remove-saved/', views.remove_saved_artist),
    path('undo-signal/', views.undo_artist_signal),
]
