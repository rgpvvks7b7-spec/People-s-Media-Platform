from decimal import Decimal

from django.db import DatabaseError
from django.db.models import F
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from artists.models import ArtistProfile
from artists.contact_utils import update_global_email_consent
from artists.themes import normalize_profile_theme
from config.platform_fees import (
    ARTIST_PRO_PLANS,
    STUDIO_PLAN_MONTHLY_CREDITS,
    fee_calculator,
    fee_schedule_for_plan,
)
from config.platform_mode import fan_registration_allowed
from config.stripe_checkout import demo_mode_allowed
from config.throttling import AuthRateThrottle, CheckoutRateThrottle
from config.upload_validation import validate_image_upload
from .artist_plan_stripe import activate_artist_plan, get_artist_plan_config, paid_artist_plan_ids
from .email_verification import send_verification_email, verification_required, verify_email_token
from .models import BetaFeedback, FanWaitlistEntry
from .beta_report import build_beta_feedback_report
from .waitlist import confirm_waitlist_token, send_waitlist_confirmation

User = get_user_model()

try:
    import stripe
except ImportError:
    stripe = None


def normalize_professions(data):
    raw_values = []
    valid_keys = ArtistProfile.valid_profession_keys()

    if hasattr(data, "getlist"):
        raw_values.extend(data.getlist("professions"))
        raw_values.extend(data.getlist("professions[]"))

    raw = data.get("professions", "")
    if isinstance(raw, list):
        raw_values.extend(raw)
    elif raw:
        raw_values.extend(str(raw).split(","))

    professions = []
    for value in raw_values:
        key = str(value).strip()
        if key in valid_keys and key not in professions:
            professions.append(key)

    return professions or [ArtistProfile.DEFAULT_PROFESSION]


def serialize_user(user, request=None):
    artist_profile = getattr(user, "artist_profile", None)

    avatar_url = user.avatar.url if user.avatar else None
    cover_url = user.cover_image.url if user.cover_image else None
    if request is not None:
        if avatar_url:
            avatar_url = request.build_absolute_uri(avatar_url)
        if cover_url:
            cover_url = request.build_absolute_uri(cover_url)

    from subscriptions.limits import active_subscription_count, subscription_limit_for

    payload = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar": avatar_url,
        "cover_image": cover_url,
        "user_type": user.user_type,
        "is_artist": user.user_type == User.ARTIST,
        "is_host": user.user_type == User.HOST,
        "artist_profile_id": artist_profile.id if artist_profile else None,
        "is_verified": artist_profile.is_verified if artist_profile else False,
        "favorite_genres": user.favorite_genres,
        "discovery_location": user.discovery_location,
        "is_beta_tester": user.is_beta_tester,
        "beta_notes": user.beta_notes,
        "artist_plan": user.artist_plan,
        "share_email_with_supported_artists": user.share_email_with_supported_artists,
        "email_share_consent_at": user.email_share_consent_at,
        "discovery_prefer_emerging": user.discovery_prefer_emerging,
        "discovery_fewer_promoted": user.discovery_fewer_promoted,
        "discovery_promoted_genres_only": user.discovery_promoted_genres_only,
        "email_verified": user.email_verified,
        "email_verification_required": verification_required(user),
        "session_login_count": getattr(user, "session_login_count", 0),
        "theme_name": getattr(user, "theme_name", "theme-indie-dark"),
        "subscription_limit": subscription_limit_for(user),
        "subscription_count": active_subscription_count(user),
    }
    return payload


def record_session_login(user):
    try:
        User.objects.filter(pk=user.pk).update(session_login_count=F("session_login_count") + 1)
        user.refresh_from_db(fields=["session_login_count"])
    except (DatabaseError, AttributeError):
        pass


def serialize_beta_feedback(feedback):
    return {
        "id": feedback.id,
        "category": feedback.category,
        "severity": feedback.severity,
        "path": feedback.path,
        "summary": feedback.summary,
        "details": feedback.details,
        "resolved": feedback.resolved,
        "created_at": feedback.created_at,
    }


@api_view(['GET'])
def index(request):
    return Response({'app': 'accounts', 'status': 'ready'})


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def register(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user_type = request.data.get("user_type") or User.FAN
    display_name = (request.data.get("display_name") or "").strip()
    email = (request.data.get("email") or "").strip()
    favorite_genres = (request.data.get("favorite_genres") or "").strip()
    discovery_location = (request.data.get("discovery_location") or request.data.get("city") or "").strip()
    share_email = request.data.get("share_email_with_supported_artists") in {True, "true", "1", "on"}

    if not username or not password:
        return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 8:
        return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

    if not display_name:
        return Response({"error": "Display name is required"}, status=status.HTTP_400_BAD_REQUEST)

    if not email:
        return Response({"error": "Email address is required"}, status=status.HTTP_400_BAD_REQUEST)

    if user_type == User.FAN and not fan_registration_allowed():
        return Response(
            {
                "error": "Fan registration opens at public launch. Join the fan waitlist or sign up as an artist or host.",
                "code": "prelaunch_fan_registration_closed",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if user_type == User.FAN:
        if not favorite_genres:
            return Response({"error": "Favorite genres are required"}, status=status.HTTP_400_BAD_REQUEST)
        if not discovery_location:
            return Response({"error": "City or region is required"}, status=status.HTTP_400_BAD_REQUEST)

    if user_type == User.HOST and not discovery_location:
        return Response({"error": "Venue city is required"}, status=status.HTTP_400_BAD_REQUEST)

    if user_type == User.ARTIST:
        stage_name = (request.data.get("stage_name") or display_name or username).strip()
        artist_city = (request.data.get("city") or "").strip()
        artist_genre = (request.data.get("genre") or "").strip()
        if not stage_name:
            return Response({"error": "Stage name is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not artist_city:
            return Response({"error": "Artist city is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not artist_genre:
            return Response({"error": "Artist genre is required"}, status=status.HTTP_400_BAD_REQUEST)

    if user_type not in {User.FAN, User.ARTIST, User.HOST}:
        return Response({"error": "Account type must be fan, artist, or host"}, status=status.HTTP_400_BAD_REQUEST)

    terms_accepted = request.data.get("terms_accepted") in {True, "true", "1", "on"}
    if not terms_accepted:
        return Response(
            {"error": "You must accept the Terms of Service and Privacy Policy to register"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            user_type=user_type,
            display_name=display_name,
            favorite_genres=favorite_genres,
            discovery_location=discovery_location,
            share_email_with_supported_artists=share_email,
            email_share_consent_at=timezone.now() if share_email else None,
            email_verified=not settings.REQUIRE_EMAIL_VERIFICATION,
            terms_accepted_at=timezone.now(),
        )
    except IntegrityError:
        return Response({"error": "Username is already taken"}, status=status.HTTP_400_BAD_REQUEST)

    if settings.REQUIRE_EMAIL_VERIFICATION:
        send_verification_email(user)

    if user.user_type == User.ARTIST:
        ArtistProfile.objects.get_or_create(
            owner=user,
            defaults={
                "stage_name": request.data.get("stage_name") or display_name or username,
                "genre": request.data.get("genre", ""),
                "city": request.data.get("city", ""),
                "artist_story": request.data.get("artist_story", ""),
                "influences": request.data.get("influences", ""),
                "professions": ",".join(normalize_professions(request.data)),
            },
        )

    if user.user_type == User.HOST:
        from spaces.models import HostProfile

        HostProfile.objects.get_or_create(
            user=user,
            defaults={
                "business_name": display_name or username,
                "city": discovery_location,
                "contact_email": email,
            },
        )

    login(request, user)
    record_session_login(user)

    message = "Account created"
    if settings.REQUIRE_EMAIL_VERIFICATION:
        message = "Account created. Check your email to verify your address before purchases."

    return Response({
        "message": message,
        "user": serialize_user(user, request),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def login_view(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response({"error": "Invalid username or password"}, status=status.HTTP_400_BAD_REQUEST)

    if user.user_type == User.ARTIST:
        ArtistProfile.objects.get_or_create(
            owner=user,
            defaults={"stage_name": user.display_name or user.username},
        )

    login(request, user)
    record_session_login(user)

    return Response({
        "message": "Logged in",
        "user": serialize_user(user, request),
    })


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"message": "Logged out"})


@never_cache
@ensure_csrf_cookie
@api_view(["GET"])
def current_user(request):
    if not request.user.is_authenticated:
        return Response({"authenticated": False, "user": None})

    try:
        from promotions.services import maybe_grant_studio_monthly_credits

        maybe_grant_studio_monthly_credits(request.user)
    except Exception:
        pass

    return Response({
        "authenticated": True,
        "user": serialize_user(request.user, request),
    })


@api_view(["POST"])
def update_profile_media(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    user = request.user
    changed = False

    if "avatar" in request.FILES:
        avatar_error = validate_image_upload(request.FILES["avatar"], "Avatar")
        if avatar_error:
            return Response({"error": avatar_error}, status=status.HTTP_400_BAD_REQUEST)
        user.avatar = request.FILES["avatar"]
        changed = True
    elif request.data.get("remove_avatar") in {True, "true", "1", "on"}:
        user.avatar = None
        changed = True

    if "cover_image" in request.FILES:
        cover_error = validate_image_upload(request.FILES["cover_image"], "Cover image")
        if cover_error:
            return Response({"error": cover_error}, status=status.HTTP_400_BAD_REQUEST)
        user.cover_image = request.FILES["cover_image"]
        changed = True
    elif request.data.get("remove_cover_image") in {True, "true", "1", "on"}:
        user.cover_image = None
        changed = True

    if not changed:
        return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)

    user.save()

    return Response({
        "message": "Profile photo updated",
        "user": serialize_user(user, request),
    })


@api_view(["POST"])
def update_profile_theme(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type == User.ARTIST:
        return Response({"error": "Artist page themes are managed from page settings."}, status=status.HTTP_400_BAD_REQUEST)

    theme_name = normalize_profile_theme(
        request.data.get("theme_name"),
        user_type=request.user.user_type,
    )
    request.user.theme_name = theme_name
    request.user.save(update_fields=["theme_name"])

    return Response({
        "message": "Profile theme saved.",
        "theme_name": theme_name,
        "user": serialize_user(request.user, request),
    })


@api_view(["GET", "POST"])
def email_preferences(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "POST":
        share_email = request.data.get("share_email_with_supported_artists") in {True, "true", "1", "on"}
        update_global_email_consent(request.user, share_email)

        update_fields = []
        if "discovery_location" in request.data:
            request.user.discovery_location = (request.data.get("discovery_location") or "").strip()[:120]
            update_fields.append("discovery_location")
        if "favorite_genres" in request.data:
            request.user.favorite_genres = (request.data.get("favorite_genres") or "").strip()[:255]
            update_fields.append("favorite_genres")
        for field in (
            "discovery_prefer_emerging",
            "discovery_fewer_promoted",
            "discovery_promoted_genres_only",
        ):
            if field in request.data:
                setattr(
                    request.user,
                    field,
                    request.data.get(field) in {True, "true", "1", "on"},
                )
                update_fields.append(field)
        if update_fields:
            request.user.save(update_fields=update_fields)

    return Response({
        "share_email_with_supported_artists": request.user.share_email_with_supported_artists,
        "email_share_consent_at": request.user.email_share_consent_at,
        "discovery_location": request.user.discovery_location,
        "favorite_genres": request.user.favorite_genres,
        "discovery_prefer_emerging": request.user.discovery_prefer_emerging,
        "discovery_fewer_promoted": request.user.discovery_fewer_promoted,
        "discovery_promoted_genres_only": request.user.discovery_promoted_genres_only,
        "user": serialize_user(request.user, request),
    })


@api_view(["GET", "POST"])
def beta_feedback(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        feedback = BetaFeedback.objects.filter(user=request.user)[:25]
        return Response({
            "results": [serialize_beta_feedback(item) for item in feedback],
            "count": feedback.count(),
        })

    summary = (request.data.get("summary") or "").strip()
    if not summary:
        return Response({"error": "Summary is required"}, status=status.HTTP_400_BAD_REQUEST)

    category = request.data.get("category") or BetaFeedback.NAVIGATION
    if category not in dict(BetaFeedback.CATEGORIES):
        category = BetaFeedback.OTHER

    severity = request.data.get("severity") or BetaFeedback.MEDIUM
    if severity not in dict(BetaFeedback.SEVERITIES):
        severity = BetaFeedback.MEDIUM

    feedback = BetaFeedback.objects.create(
        user=request.user,
        category=category,
        severity=severity,
        path=(request.data.get("path") or "")[:255],
        summary=summary[:180],
        details=(request.data.get("details") or "").strip(),
        user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:1000],
    )

    request.user.is_beta_tester = True
    request.user.save(update_fields=["is_beta_tester"])

    return Response({
        "message": "Thanks, beta feedback recorded.",
        "feedback": serialize_beta_feedback(feedback),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def beta_feedback_summary(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ADMIN and not request.user.is_staff:
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    return Response(build_beta_feedback_report())


@api_view(["POST"])
def beta_feedback_resolve(request, feedback_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ADMIN and not request.user.is_staff:
        return Response({"error": "Admin access required"}, status=status.HTTP_403_FORBIDDEN)

    try:
        feedback = BetaFeedback.objects.get(id=feedback_id)
    except BetaFeedback.DoesNotExist:
        return Response({"error": "Feedback not found"}, status=status.HTTP_404_NOT_FOUND)

    feedback.resolved = bool(request.data.get("resolved", True))
    feedback.save(update_fields=["resolved"])

    return Response({
        "message": "Feedback resolved." if feedback.resolved else "Feedback reopened.",
        "feedback": serialize_beta_feedback(feedback),
        "summary": build_beta_feedback_report(),
    })


@api_view(["GET"])
def artist_plans(request):
    return Response({
        "free": {
            "id": "free",
            "name": "Free",
            "monthly_price": "0.00",
            "features": ["Basic profile", "Music and arts pages", "$1 fan support", "Basic store"],
        },
        "paid": [
            {
                "id": plan["id"],
                "name": plan["name"],
                "monthly_price": str(plan["monthly_price"]),
                "features": plan["features"],
                "monthly_promotion_credits": str(STUDIO_PLAN_MONTHLY_CREDITS)
                if plan["id"] == "studio"
                else "0.00",
            }
            for plan in ARTIST_PRO_PLANS
        ],
    })


@api_view(["GET"])
def public_fee_schedule(request):
    """Public fee table + keep-vs-fee calculator for the pricing page."""
    plan = (request.query_params.get("plan") or "free").strip().lower()
    schedule = fee_schedule_for_plan(plan)
    calculator = fee_calculator(
        schedule["plan"],
        support_gmv=request.query_params.get("support_gmv") or "0",
        tips_gmv=request.query_params.get("tips_gmv") or "0",
        marketplace_gmv=request.query_params.get("marketplace_gmv") or "0",
    )
    return Response({
        "schedule": schedule,
        "calculator": calculator,
        "plans": ["free", "pro", "studio"],
    })


@api_view(["POST"])
def update_artist_plan(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    plan = (request.data.get("plan") or "").strip()
    valid_plans = {"free", "pro", "studio"}
    if plan not in valid_plans:
        return Response({"error": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

    if plan != "free" and not settings.DEBUG:
        return Response(
            {"error": "Paid artist plans are not available for self-service upgrade yet."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    request.user.artist_plan = plan
    request.user.save(update_fields=["artist_plan"])

    grant = None
    if plan == "studio":
        try:
            from promotions.services import maybe_grant_studio_monthly_credits, wallet_balance

            grant = maybe_grant_studio_monthly_credits(request.user)
            balance = wallet_balance(request.user)
        except Exception:
            balance = None
    else:
        balance = None

    return Response({
        "message": f"Artist plan updated to {plan}.",
        "user": serialize_user(request.user, request),
        "studio_credits_granted": str(STUDIO_PLAN_MONTHLY_CREDITS) if grant else None,
        "promotion_balance": str(balance.quantize(Decimal("0.01"))) if balance is not None else None,
    })


@api_view(["POST"])
@throttle_classes([CheckoutRateThrottle])
def artist_plan_checkout(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    plan = (request.data.get("plan") or "").strip()
    if plan not in paid_artist_plan_ids():
        return Response({"error": "Invalid paid plan."}, status=status.HTTP_400_BAD_REQUEST)

    plan_config = get_artist_plan_config(plan)
    monthly_price = plan_config["monthly_price"]

    if demo_mode_allowed():
        grant, balance = activate_artist_plan(request.user, plan)
        return Response({
            "demo": True,
            "message": f"{plan_config['name']} activated (demo).",
            "user": serialize_user(request.user, request),
            "studio_credits_granted": str(STUDIO_PLAN_MONTHLY_CREDITS) if grant else None,
            "promotion_balance": str(balance.quantize(Decimal("0.01"))) if balance is not None else None,
        })

    if stripe is None or not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount_cents = int(monthly_price * Decimal("100"))
    metadata = {
        "purchase_type": "artist_plan",
        "user_id": str(request.user.id),
        "plan": plan,
    }

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            success_url=f"{settings.FRONTEND_URL}/?plan=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/?plan=cancelled",
            customer_email=request.user.email or None,
            line_items=[{
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {"name": plan_config["name"]},
                    "unit_amount": amount_cents,
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            metadata=metadata,
            subscription_data={"metadata": metadata},
        )
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
    })


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def verify_email(request):
    token = (request.data.get("token") or "").strip()
    user, error = verify_email_token(token)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    if request.user.is_authenticated and request.user.id == user.id:
        pass
    elif not request.user.is_authenticated:
        login(request, user)

    return Response({
        "message": "Email verified.",
        "user": serialize_user(user, request),
    })


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def resend_verification_email(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.email_verified:
        return Response({"message": "Email is already verified."})

    sent = send_verification_email(request.user)
    if not sent:
        return Response({"error": "Could not send verification email."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"message": "Verification email sent."})


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def password_reset_request(request):
    email = (request.data.get("email") or "").strip()
    username = (request.data.get("username") or "").strip()

    user = None
    if email:
        user = User.objects.filter(email__iexact=email).first()
    elif username:
        user = User.objects.filter(username__iexact=username).first()

    if user and user.email:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        frontend_url = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
        reset_url = f"{frontend_url}/?reset-password={uid}/{token}"
        send_mail(
            subject="Reset your IndieFund password",
            message=(
                f"Hi {user.display_name or user.username},\n\n"
                f"Reset your password: {reset_url}\n\n"
                "If you did not request this, ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

    return Response({"message": "If an account exists, a reset link was sent."})


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def password_reset_confirm(request):
    uid = (request.data.get("uid") or "").strip()
    token = (request.data.get("token") or "").strip()
    password = request.data.get("password") or ""

    if len(password) < 8:
        return Response({"error": "Password must be at least 8 characters"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({"error": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save(update_fields=["password"])

    return Response({"message": "Password updated. You can log in now."})


def serialize_waitlist_entry(entry):
    return {
        "id": entry.id,
        "email": entry.email,
        "city": entry.city,
        "favorite_genres": entry.favorite_genres,
        "confirmed": entry.confirmed,
        "created_at": entry.created_at,
    }


@api_view(["POST"])
@throttle_classes([AuthRateThrottle])
def fan_waitlist_join(request):
    if fan_registration_allowed():
        return Response(
            {
                "error": "Fan registration is open — create a free fan account instead.",
                "code": "waitlist_closed",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = (request.data.get("email") or "").strip().lower()
    city = (request.data.get("city") or request.data.get("discovery_location") or "").strip()
    favorite_genres = (request.data.get("favorite_genres") or "").strip()
    source = (request.data.get("source") or "prelaunch").strip()[:40]

    if not email:
        return Response({"error": "Email address is required"}, status=status.HTTP_400_BAD_REQUEST)

    terms_accepted = request.data.get("terms_accepted") in {True, "true", "1", "on"}
    if not terms_accepted:
        return Response(
            {"error": "You must accept the Privacy Policy to join the waitlist"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = FanWaitlistEntry.objects.filter(email=email).first()
    if existing:
        if existing.confirmed:
            return Response(
                {
                    "message": "You are already on the launch waitlist.",
                    "entry": serialize_waitlist_entry(existing),
                    "already_registered": True,
                }
            )
        existing.city = city or existing.city
        existing.favorite_genres = favorite_genres or existing.favorite_genres
        existing.source = source or existing.source
        existing.save(update_fields=["city", "favorite_genres", "source", "updated_at"])
        send_waitlist_confirmation(existing)
        return Response(
            {
                "message": "Check your email to confirm your waitlist spot.",
                "entry": serialize_waitlist_entry(existing),
                "confirmation_sent": True,
            },
            status=status.HTTP_200_OK,
        )

    entry = FanWaitlistEntry.objects.create(
        email=email,
        city=city,
        favorite_genres=favorite_genres,
        source=source,
    )
    email_sent = send_waitlist_confirmation(entry)
    message = (
        "Check your email to confirm your waitlist spot."
        if email_sent
        else "You are on the launch waitlist. We will email you when fans can join."
    )
    return Response(
        {
            "message": message,
            "entry": serialize_waitlist_entry(entry),
            "confirmation_sent": email_sent,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "POST"])
def fan_waitlist_confirm(request):
    token = (request.data.get("token") if request.method == "POST" else None) or request.query_params.get("token") or ""
    token = token.strip()
    entry, error = confirm_waitlist_token(token)
    if error:
        return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
    return Response(
        {
            "message": "Waitlist email confirmed. We will notify you when fan features open.",
            "entry": serialize_waitlist_entry(entry),
        }
    )
