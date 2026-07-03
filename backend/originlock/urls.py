from django.urls import path

from . import views

urlpatterns = [
    path("pending/", views.pending_releases),
    path("releases/<int:approval_id>/", views.release_detail),
    path("releases/<int:approval_id>/seal/", views.seal_release_view),
    path("passkeys/", views.passkey_list),
    path("passkeys/register/begin/", views.passkey_register_begin),
    path("passkeys/register/complete/", views.passkey_register_complete),
    path("passkeys/authenticate/begin/", views.passkey_authenticate_begin),
]
