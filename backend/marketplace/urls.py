from django.urls import path
from .views import commission_requests, create_cart_checkout, create_product, create_purchase_checkout, download_product_file, my_purchases, product_list, purchase_product, update_commission_request

urlpatterns = [
    path("", product_list),
    path("create/", create_product),
    path("files/<int:product_id>/download/", download_product_file),
    path("cart-checkout/", create_cart_checkout),
    path("checkout/", create_purchase_checkout),
    path("purchase/", purchase_product),
    path("my-purchases/", my_purchases),
    path("commissions/", commission_requests),
    path("commissions/<int:commission_id>/update/", update_commission_request),
]
