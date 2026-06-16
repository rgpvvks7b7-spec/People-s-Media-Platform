from django.urls import path
from .views import create_comment, create_post, post_list, toggle_like

urlpatterns = [
    path("", post_list),
    path("create/", create_post),
    path("<int:post_id>/comment/", create_comment),
    path("<int:post_id>/toggle-like/", toggle_like),
]
