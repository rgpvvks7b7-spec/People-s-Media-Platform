from django.urls import path
from .views import (
    add_playlist_track,
    artwork_list,
    create_artwork,
    create_music,
    create_song_cover,
    fan_playlists,
    fan_radio_tracks,
    music_list,
    record_music_event,
    remove_playlist_track,
    set_default_song_cover,
    song_cover_list,
    stream_track,
)

urlpatterns = [
    path("", music_list),
    path("create/", create_music),
    path("tracks/<int:track_id>/stream/", stream_track),
    path("radio/", fan_radio_tracks),
    path("events/", record_music_event),
    path("playlists/", fan_playlists),
    path("playlists/<int:playlist_id>/add-track/", add_playlist_track),
    path("playlists/<int:playlist_id>/remove-track/", remove_playlist_track),
    path("artworks/", artwork_list),
    path("artworks/create/", create_artwork),
    path("cover-art/", song_cover_list),
    path("cover-art/create/", create_song_cover),
    path("cover-art/<int:cover_id>/set-default/", set_default_song_cover),
]
