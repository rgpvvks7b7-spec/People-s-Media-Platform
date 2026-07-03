from django.urls import path

from . import views

urlpatterns = [
    path("reports/", views.reports),
    path("reports/<int:report_id>/resolve/", views.resolve_report),
    path("blocks/", views.blocks),
    path("blocks/unblock/", views.unblock),
    path("mutes/", views.mutes),
    path("mutes/unmute/", views.unmute),
]
