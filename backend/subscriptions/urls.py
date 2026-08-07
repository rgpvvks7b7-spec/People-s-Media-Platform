from django.urls import path
from .views import (
    admin_refund,
    create_billing_portal_session,
    create_checkout_session,
    extend_limit,
    stripe_webhook,
    subscription_list,
    subscribe_to_artist,
    support_tiers,
    tips,
    unsubscribe_from_artist,
)

urlpatterns = [
    path("", subscription_list),
    path("subscribe/", subscribe_to_artist),
    path("checkout/", create_checkout_session),
    path("extend-limit/", extend_limit),
    path("tiers/", support_tiers),
    path("tips/", tips),
    path("billing-portal/", create_billing_portal_session),
    path("unsubscribe/", unsubscribe_from_artist),
    path("stripe-webhook/", stripe_webhook),
    path("admin/refund/", admin_refund),
]
