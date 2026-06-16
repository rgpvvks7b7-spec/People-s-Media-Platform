from django.urls import path
from .views import product_list, create_product

urlpatterns = [
    path("", product_list),
    path("create/", create_product),
]
