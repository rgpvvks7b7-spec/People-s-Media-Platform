from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),
    path('register/', views.register),
    path('login/', views.login_view),
    path('logout/', views.logout_view),
    path('current-user/', views.current_user),
]
