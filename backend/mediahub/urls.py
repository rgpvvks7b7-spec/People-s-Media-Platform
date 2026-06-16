from django.urls import path
from .views import create_music, music_list

urlpatterns = [
    path("", music_list),
    path("create/", create_music),
]
