from django.urls import path

from . import views

urlpatterns = [
    path("host-profile/", views.host_profile, name="spaces-host-profile"),
    path("listings/", views.listings, name="spaces-listings"),
    path("listings/followed/", views.followed_listings, name="spaces-listings-followed"),
    path("listings/<int:listing_id>/", views.listing_detail, name="spaces-listing-detail"),
    path("listings/<int:listing_id>/follow/", views.listing_follow, name="spaces-listing-follow"),
    path("listings/<int:listing_id>/unfollow/", views.listing_unfollow, name="spaces-listing-unfollow"),
    path("listings/<int:listing_id>/photos/<int:photo_id>/", views.listing_photo_detail, name="spaces-listing-photo-detail"),
    path("bookings/", views.bookings, name="spaces-bookings"),
    path("bookings/clear/", views.clear_bookings, name="spaces-bookings-clear"),
    path("bookings/<int:booking_id>/dismiss/", views.dismiss_booking, name="spaces-booking-dismiss"),
    path("bookings/<int:booking_id>/status/", views.booking_status, name="spaces-booking-status"),
    path("bookings/<int:booking_id>/notify-local-supporters/", views.notify_local_supporters, name="spaces-notify-local-supporters"),
    path("bookings/<int:booking_id>/reviews/", views.booking_reviews, name="spaces-booking-reviews"),
    path("bookings/<int:booking_id>/check-in/", views.booking_check_in, name="spaces-booking-check-in"),
    path("bookings/<int:booking_id>/ticket-stub/", views.create_booking_ticket_stub, name="spaces-booking-ticket-stub"),
    path("artists/<int:artist_id>/draw-profile/", views.draw_profile, name="spaces-draw-profile"),
    path("host-earnings/", views.host_earnings, name="spaces-host-earnings"),
]
