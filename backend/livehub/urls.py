from django.urls import path

from . import views

urlpatterns = [
    path("", views.session_list),
    path("start/", views.start_session),
    path("<int:session_id>/", views.session_detail),
    path("<int:session_id>/stop/", views.stop_session),
    path("<int:session_id>/chat/", views.chat_messages),
]
