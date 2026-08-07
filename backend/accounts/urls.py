from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('register/', views.register),
    path('login/', views.login_view),
    path('logout/', views.logout_view),
    path('current-user/', views.current_user),
    path('profile-media/', views.update_profile_media),
    path('profile-theme/', views.update_profile_theme),
    path('email-preferences/', views.email_preferences),
    path('beta-feedback/', views.beta_feedback),
    path('beta-feedback/summary/', views.beta_feedback_summary),
    path('beta-feedback/<int:feedback_id>/resolve/', views.beta_feedback_resolve),
    path('artist-plans/', views.artist_plans),
    path('fee-schedule/', views.public_fee_schedule),
    path('artist-plan/', views.update_artist_plan),
    path('artist-plan/checkout/', views.artist_plan_checkout),
    path('verify-email/', views.verify_email),
    path('resend-verification/', views.resend_verification_email),
    path('password-reset/', views.password_reset_request),
    path('password-reset/confirm/', views.password_reset_confirm),
    path('waitlist/', views.fan_waitlist_join),
    path('waitlist/confirm/', views.fan_waitlist_confirm),
]
