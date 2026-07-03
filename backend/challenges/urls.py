from django.urls import path

from .views import claim, today


urlpatterns = [
    path("today/", today),
    path("claim/", claim),
]
