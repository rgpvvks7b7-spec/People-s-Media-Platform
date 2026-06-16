from django.urls import path
from .views import create_billing_portal_session, create_checkout_session, stripe_webhook, subscription_list, subscribe_to_artist, unsubscribe_from_artist

urlpatterns = [
    path("", subscription_list),
    path("subscribe/", subscribe_to_artist),
    path("checkout/", create_checkout_session),
    path("billing-portal/", create_billing_portal_session),
    path("unsubscribe/", unsubscribe_from_artist),
    path("stripe-webhook/", stripe_webhook),
]
