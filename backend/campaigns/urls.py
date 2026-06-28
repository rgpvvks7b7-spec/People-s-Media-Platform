from django.urls import path

from . import views

urlpatterns = [
    path("", views.campaign_list_create),
    path("<int:campaign_id>/", views.campaign_detail),
    path("<int:campaign_id>/update/", views.campaign_update),
    path("<int:campaign_id>/delete/", views.campaign_delete),
]
