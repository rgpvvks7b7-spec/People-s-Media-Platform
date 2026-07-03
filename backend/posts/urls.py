from django.urls import path
from .views import create_comment, create_post, delete_instant, delete_post, instant_list, point_of_view_list, post_list, report_instant, toggle_like

urlpatterns = [
    path("", post_list),
    path("create/", create_post),
    path("pov/", point_of_view_list),
    path("instants/", instant_list),
    path("instants/<int:instant_id>/report/", report_instant),
    path("instants/<int:instant_id>/delete/", delete_instant),
    path("<int:post_id>/comment/", create_comment),
    path("<int:post_id>/toggle-like/", toggle_like),
    path("<int:post_id>/delete/", delete_post),
]
