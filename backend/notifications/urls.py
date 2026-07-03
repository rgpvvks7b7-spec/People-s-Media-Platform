from django.urls import path

from . import views

urlpatterns = [
    path("", views.notification_list),
    path("mark-read/", views.mark_read),
    path("clear/", views.clear_notifications),
    path("push/vapid/", views.push_vapid_public_key),
    path("push/subscribe/", views.push_subscribe),
    path("push/unsubscribe/", views.push_unsubscribe),
]
