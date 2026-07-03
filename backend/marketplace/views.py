from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import FileResponse, Http404
from decimal import Decimal, InvalidOperation
from .models import CommissionRequest, Product
from .purchase_flow import complete_product_purchase, fan_already_purchased_product, ticket_sale_split
from artists.models import ArtistProfile
from artists.journey import log_fan_journey_event
from artists.models import FanJourneyEvent
from config.platform_fees import MARKETPLACE_PLATFORM_RATE, TICKET_PLATFORM_RATE, split_amount
from config.platform_mode import fan_experience_guard
from config.billing_guard import billing_allowed
from config.stripe_checkout import (
    build_checkout_session,
    checkout_payment_intent_data,
    checkout_payment_intent_data_with_fees,
    connect_account_for_artist,
    demo_mode_allowed,
)
from notifications.services import notify_opted_in_supporters
from subscriptions.models import FanSubscription
from config.media_access import build_signed_file_url, parse_file_access_token
from originlock.models import MediaAccessLog, ReleaseApproval
from originlock.protection import (
    compute_acoustic_fingerprint,
    log_media_access,
    serialize_protection,
)
from originlock.services import (
    approvals_for,
    compute_file_sha256,
    create_pending_approval,
    get_approval_for,
    origin_badges,
    serialize_origin_lock,
)

try:
    import stripe
except ImportError:
    stripe = None

User = get_user_model()

MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_AUDIO_SIZE = 50 * 1024 * 1024
MAX_PRODUCT_FILE_SIZE = 200 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
ALLOWED_PRODUCT_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS | {".zip"}


def validate_upload(file_obj, allowed_extensions, max_size, label):
    if not file_obj:
        return None

    name = file_obj.name.lower()
    if not any(name.endswith(ext) for ext in allowed_extensions):
        return f"{label} must be one of: {', '.join(sorted(allowed_extensions))}"

    if file_obj.size > max_size:
        return f"{label} is too large."

    return None


def normalize_profession(user, value):
    profession = (value or ArtistProfile.DEFAULT_PROFESSION).strip()
    if profession not in ArtistProfile.valid_profession_keys():
        return None

    if user.is_authenticated and user.user_type == "artist":
        try:
            if user.artist_profile.has_profession(profession):
                return profession
        except ArtistProfile.DoesNotExist:
            pass

    return None


def has_access(user, artist, profession):
    if user.is_authenticated and user == artist:
        return True

    if not user.is_authenticated:
        return False

    return FanSubscription.objects.filter(
        fan=user,
        artist=artist,
        profession=profession,
        active=True,
    ).exists()


def product_download_allowed(user, product, is_owner):
    """Paid download copies require a purchase unless the artist opts out."""
    if is_owner:
        return True
    if not product.download_requires_purchase:
        return True
    if not user.is_authenticated:
        return False
    return fan_already_purchased_product(user, product.id)


def parse_decimal_or_none(value):
    if value in {None, ""}:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def request_bool(data, field, default=False):
    value = data.get(field, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def serialize_commission_request(item):
    return {
        "id": item.id,
        "fan_id": item.fan.id,
        "fan_username": item.fan.username,
        "artist_id": item.artist.id,
        "artist_username": item.artist.username,
        "profession": item.profession,
        "profession_label": ArtistProfile.profession_label(item.profession),
        "title": item.title,
        "brief": item.brief,
        "budget": str(item.budget) if item.budget is not None else "",
        "deadline": item.deadline,
        "size_format": item.size_format,
        "reference_notes": item.reference_notes,
        "reference_links": item.reference_links,
        "delivery_notes": item.delivery_notes,
        "shipping_required": item.shipping_required,
        "status": item.status,
        "status_label": dict(CommissionRequest.STATUSES).get(item.status, "New"),
        "artist_response": item.artist_response,
        "quoted_price": str(item.quoted_price) if item.quoted_price is not None else "",
        "quoted_artist_share": str(item.quoted_artist_share) if item.quoted_artist_share is not None else "",
        "quoted_platform_fee": str(item.quoted_platform_fee) if item.quoted_platform_fee is not None else "",
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }

@api_view(["GET"])
def product_list(request):
    products = list(Product.objects.select_related("artist").filter(is_active=True).order_by("-created_at"))
    approvals = approvals_for(Product, [product.id for product in products])

    data = []
    for product in products:
        approval = approvals.get(product.id)
        is_owner = request.user.is_authenticated and request.user == product.artist
        released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
        if not released and not is_owner:
            continue

        can_access = (not product.is_supporter_only) or has_access(request.user, product.artist, product.profession)
        show_files = can_access and (released or is_owner)
        can_download = show_files and product.product_file and product_download_allowed(request.user, product, is_owner)
        product_file_url = (
            build_signed_file_url(request, "product", product.id)
            if can_download
            else None
        )
        preview_audio_url = (
            build_signed_file_url(request, "product_preview", product.id, access="preview")
            if product.preview_audio and show_files
            else None
        )
        badges = origin_badges(approval)
        data.append({
            "id": product.id,
            "artist_id": product.artist.id,
            "artist_username": product.artist.username,
            "profession": product.profession,
            "profession_label": ArtistProfile.profession_label(product.profession),
            "product_type": product.product_type,
            "title": product.title,
            "description": product.description,
            "price": str(product.price),
            "artist_share": str(product.artist_share),
            "platform_fee": str(product.platform_fee),
            "host_share": str(product.host_share),
            "image": request.build_absolute_uri(product.image.url) if product.image else None,
            "preview_audio": preview_audio_url,
            "product_file": product_file_url,
            "can_download": bool(can_download),
            "external_url": product.external_url,
            "external_discount_code": product.external_discount_code,
            "stock_quantity": product.stock_quantity,
            "sizes": product.sizes,
            "shipping_required": product.shipping_required,
            "eligibility_months": product.eligibility_months,
            "fulfillment_status": product.fulfillment_status,
            "fulfillment_notes": product.fulfillment_notes,
            "is_supporter_only": product.is_supporter_only,
            "can_access": can_access,
            "access_message": "" if can_access else "Supporters only",
            "bpm": product.bpm,
            "music_key": product.music_key,
            "license_type": product.license_type,
            "created_at": product.created_at,
            "release_status": approval.approval_status if approval else ReleaseApproval.APPROVED,
            "origin_lock": serialize_origin_lock(approval),
            "origin_badges": badges,
            "protection": serialize_protection(product, badges=badges),
        })

    return Response(data)


@api_view(["GET"])
def download_product_file(request, product_id):
    kind, token_object_id, access = parse_file_access_token(request.GET.get("token", ""))
    if kind != "product" or token_object_id != product_id or access != "full":
        return Response({"error": "Invalid or expired download token"}, status=status.HTTP_403_FORBIDDEN)

    try:
        product = Product.objects.select_related("artist").get(id=product_id)
    except Product.DoesNotExist:
        raise Http404

    if not product.product_file:
        raise Http404

    is_owner = request.user.is_authenticated and request.user == product.artist
    approval = get_approval_for(product)
    released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
    if not released and not is_owner:
        return Response({"error": "This release has not been finalised yet."}, status=status.HTTP_403_FORBIDDEN)

    can_access = (not product.is_supporter_only) or has_access(request.user, product.artist, product.profession)
    if not can_access:
        return Response({"error": "Supporters only"}, status=status.HTTP_403_FORBIDDEN)

    if not product_download_allowed(request.user, product, is_owner):
        return Response({"error": "Purchase required to download this file."}, status=status.HTTP_403_FORBIDDEN)

    log_media_access(request, product, product.artist, MediaAccessLog.DOWNLOAD)
    return FileResponse(product.product_file.open("rb"), as_attachment=True)


@api_view(["GET"])
def preview_product_audio(request, product_id):
    kind, token_object_id, access = parse_file_access_token(request.GET.get("token", ""))
    if kind != "product_preview" or token_object_id != product_id or access != "preview":
        return Response({"error": "Invalid or expired preview token"}, status=status.HTTP_403_FORBIDDEN)

    try:
        product = Product.objects.select_related("artist").get(id=product_id)
    except Product.DoesNotExist:
        raise Http404

    if not product.preview_audio:
        raise Http404

    is_owner = request.user.is_authenticated and request.user == product.artist
    approval = get_approval_for(product)
    released = approval is None or approval.approval_status == ReleaseApproval.APPROVED
    if not released and not is_owner:
        return Response({"error": "This release has not been finalised yet."}, status=status.HTTP_403_FORBIDDEN)

    can_access = (not product.is_supporter_only) or has_access(request.user, product.artist, product.profession)
    if not can_access:
        return Response({"error": "Supporters only"}, status=status.HTTP_403_FORBIDDEN)

    log_media_access(request, product, product.artist, MediaAccessLog.PREVIEW)

    name = product.preview_audio.name.lower()
    content_type = "audio/mpeg"
    if name.endswith(".wav"):
        content_type = "audio/wav"
    elif name.endswith(".ogg"):
        content_type = "audio/ogg"
    elif name.endswith(".flac"):
        content_type = "audio/flac"
    elif name.endswith(".m4a") or name.endswith(".aac"):
        content_type = "audio/mp4"

    return FileResponse(product.preview_audio.open("rb"), content_type=content_type)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def create_product(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    image = request.FILES.get("image")
    preview_audio = request.FILES.get("preview_audio")
    product_file = request.FILES.get("product_file")

    for error in [
        validate_upload(image, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, "Image"),
        validate_upload(preview_audio, ALLOWED_AUDIO_EXTENSIONS, MAX_AUDIO_SIZE, "Preview audio"),
        validate_upload(product_file, ALLOWED_PRODUCT_EXTENSIONS, MAX_PRODUCT_FILE_SIZE, "Product file"),
    ]:
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

    profession = normalize_profession(request.user, request.data.get("profession"))
    if not profession:
        return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    product = Product.objects.create(
        artist=request.user,
        profession=profession,
        product_type=request.data.get("product_type", Product.MERCH),
        title=request.data.get("title", "Untitled Product"),
        description=request.data.get("description", ""),
        price=request.data.get("price", "1.00"),
        image=image,
        preview_audio=preview_audio,
        product_file=product_file,
        file_hash_sha256=compute_file_sha256(product_file) if product_file else "",
        acoustic_fingerprint=compute_acoustic_fingerprint(product_file) if product_file else "",
        external_url=request.data.get("external_url", ""),
        external_discount_code=request.data.get("external_discount_code", ""),
        stock_quantity=request.data.get("stock_quantity", 0) or 0,
        sizes=request.data.get("sizes", ""),
        shipping_required=request.data.get("shipping_required") == "true",
        eligibility_months=request.data.get("eligibility_months", 0) or 0,
        fulfillment_status=request.data.get("fulfillment_status", "not_started"),
        fulfillment_notes=request.data.get("fulfillment_notes", ""),
        is_supporter_only=request.data.get("is_supporter_only") == "true",
        bpm=request.data.get("bpm") or None,
        music_key=request.data.get("music_key", ""),
        license_type=request.data.get("license_type", ""),
    )

    response_payload = {
        "message": "Product created",
        "id": product.id,
        "title": product.title,
        "product_type": product.product_type,
        "price": str(product.price),
        "artist_share": str(product.artist_share),
        "platform_fee": str(product.platform_fee),
        "host_share": str(product.host_share),
    }

    if product_file:
        # Digital downloads must be sealed by the artist before going public.
        approval = create_pending_approval(
            request.user,
            product,
            product_file,
            file_name=product_file.name,
        )
        response_payload.update({
            "message": "Product created. Finalise your release to publish it.",
            "release_approval_id": approval.id,
            "release_status": approval.approval_status,
        })
    else:
        notify_opted_in_supporters(
            request.user,
            notification_type="store",
            title=f"New store drop: {product.title}",
            body=f"{request.user.display_name or request.user.username} added a new item.",
            target_url=f"/?artist={request.user.username}",
        )

    return Response(response_payload, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def commission_requests(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.method == "GET":
        if request.user.user_type == "artist":
            queryset = CommissionRequest.objects.select_related("fan", "artist").filter(artist=request.user)
        else:
            queryset = CommissionRequest.objects.select_related("fan", "artist").filter(fan=request.user)

        return Response({
            "results": [serialize_commission_request(item) for item in queryset],
            "count": queryset.count(),
        })

    artist_id = request.data.get("artist_id")
    profession = request.data.get("profession") or ArtistProfile.VISUAL_ART
    title = (request.data.get("title") or "").strip()
    brief = (request.data.get("brief") or "").strip()

    if not title or not brief:
        return Response({"error": "Title and brief are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        artist = User.objects.get(id=artist_id, user_type=User.ARTIST)
        artist_profile = artist.artist_profile
    except (User.DoesNotExist, ArtistProfile.DoesNotExist):
        return Response({"error": "Artist profile not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user == artist:
        return Response({"error": "You cannot request a commission from yourself"}, status=status.HTTP_400_BAD_REQUEST)

    if profession == ArtistProfile.MUSIC:
        return Response({"error": "Commission requests are for arts and creative services."}, status=status.HTTP_400_BAD_REQUEST)

    if not artist_profile.has_profession(profession):
        return Response({"error": "Artist does not offer this profession"}, status=status.HTTP_400_BAD_REQUEST)

    item = CommissionRequest.objects.create(
        fan=request.user,
        artist=artist,
        profession=profession,
        title=title[:160],
        brief=brief,
        budget=parse_decimal_or_none(request.data.get("budget")),
        deadline=request.data.get("deadline") or None,
        size_format=(request.data.get("size_format") or "").strip(),
        reference_notes=(request.data.get("reference_notes") or "").strip(),
        reference_links=(request.data.get("reference_links") or "").strip(),
        delivery_notes=(request.data.get("delivery_notes") or "").strip(),
        shipping_required=request_bool(request.data, "shipping_required"),
    )

    return Response({
        "message": "Commission request sent.",
        "commission": serialize_commission_request(item),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def update_commission_request(request, commission_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        item = CommissionRequest.objects.select_related("fan", "artist").get(id=commission_id)
    except CommissionRequest.DoesNotExist:
        return Response({"error": "Commission request not found"}, status=status.HTTP_404_NOT_FOUND)

    if item.artist != request.user:
        return Response({"error": "Only the artist can update this request"}, status=status.HTTP_403_FORBIDDEN)

    next_status = request.data.get("status") or item.status
    if next_status not in dict(CommissionRequest.STATUSES):
        return Response({"error": "Invalid commission status"}, status=status.HTTP_400_BAD_REQUEST)

    item.status = next_status
    item.artist_response = (request.data.get("artist_response") or item.artist_response).strip()
    if "quoted_price" in request.data:
        item.quoted_price = parse_decimal_or_none(request.data.get("quoted_price"))
    item.save()

    return Response({
        "message": "Commission request updated.",
        "commission": serialize_commission_request(item),
    })


CART_EXCLUDED_TYPES = {
    Product.EVENT_TICKET,
    Product.EXTERNAL_FULFILLMENT,
    Product.GELATO_POD,
    Product.SHOPIFY_STORE,
    Product.PRINTIFY_POD,
    Product.FOURTHWALL_STORE,
    Product.BANDCAMP_STORE,
    Product.PRINTFUL_POD,
}


def load_cart_products(user, product_ids):
    if not product_ids:
        return None, Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

    unique_ids = []
    for product_id in product_ids:
        try:
            parsed = int(product_id)
        except (TypeError, ValueError):
            return None, Response({"error": "Invalid product id in cart."}, status=status.HTTP_400_BAD_REQUEST)
        if parsed not in unique_ids:
            unique_ids.append(parsed)

    products = list(
        Product.objects
        .select_related("artist")
        .filter(id__in=unique_ids, is_active=True)
    )
    if len(products) != len(unique_ids):
        return None, Response({"error": "One or more cart items were not found."}, status=status.HTTP_404_NOT_FOUND)

    for product in products:
        if product.product_type in CART_EXCLUDED_TYPES or product.external_url:
            return None, Response({"error": f"{product.title} must be purchased directly, not via cart."}, status=status.HTTP_400_BAD_REQUEST)
        if product.is_supporter_only and not has_access(user, product.artist, product.profession):
            return None, Response({"error": f"Supporters only: {product.title}"}, status=status.HTTP_403_FORBIDDEN)

    return products, None


def handle_cart_checkout(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    allowed, billing_error = billing_allowed(request.user)
    if not allowed:
        return Response({"error": billing_error}, status=status.HTTP_403_FORBIDDEN)

    products, error_response = load_cart_products(request.user, request.data.get("product_ids") or [])
    if error_response:
        return error_response

    if demo_mode_allowed():
        receipts = []
        for product in products:
            receipt, error = complete_product_purchase(request.user, product, payment_provider="demo")
            if error == "sold_out":
                return Response({"error": f"Sold out: {product.title}", "sold_out": True}, status=status.HTTP_409_CONFLICT)
            if error == "already_purchased":
                return Response({"error": f"Already purchased: {product.title}", "already_purchased": True}, status=status.HTTP_409_CONFLICT)
            receipts.append(receipt)
        total = sum(Decimal(item["amount"]) for item in receipts)
        return Response({
            "demo": True,
            "message": f"Cart purchase recorded ({len(receipts)} items).",
            "receipts": receipts,
            "count": len(receipts),
            "total": str(total),
        }, status=status.HTTP_201_CREATED)

    if stripe is None:
        return Response({"error": "Stripe package is not installed. Run pip install -r requirements.txt."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured. Set STRIPE_SECRET_KEY."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    stripe.api_key = settings.STRIPE_SECRET_KEY
    line_items = []
    for product in products:
        line_items.append({
            "price_data": {
                "currency": settings.STRIPE_CURRENCY,
                "product_data": {
                    "name": product.title,
                    "description": f"From {product.artist.username}",
                },
                "unit_amount": int(product.price * Decimal("100")),
            },
            "quantity": 1,
        })

    product_ids = ",".join(str(product.id) for product in products)
    artist_ids = {product.artist_id for product in products}
    connect_account_id = None
    payment_intent_data = None
    if len(artist_ids) == 1:
        connect_account_id = connect_account_for_artist(products[0].artist)
        if connect_account_id:
            application_fee = Decimal("0.00")
            for product in products:
                _, platform_fee, host_share = ticket_sale_split(product)
                application_fee += platform_fee + host_share
            payment_intent_data = checkout_payment_intent_data_with_fees(application_fee, connect_account_id)
    elif not settings.DEBUG:
        return Response(
            {"error": "Checkout one artist at a time until split payouts are supported."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        session_kwargs = {
            "mode": "payment",
            "success_url": f"{settings.FRONTEND_URL}/?purchase=success&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{settings.FRONTEND_URL}/?purchase=cancelled",
            "client_reference_id": f"cart:{request.user.id}:{product_ids}",
            "customer_email": request.user.email or None,
            "line_items": line_items,
            "metadata": {
                "purchase_type": "marketplace_cart",
                "fan_id": str(request.user.id),
                "product_ids": product_ids,
            },
        }
        if payment_intent_data:
            session_kwargs["payment_intent_data"] = payment_intent_data
        checkout_session = build_checkout_session(**session_kwargs)
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
        "count": len(products),
    })


def handle_purchase_checkout(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    blocked = fan_experience_guard(request)
    if blocked:
        return blocked

    allowed, billing_error = billing_allowed(request.user)
    if not allowed:
        return Response({"error": billing_error}, status=status.HTTP_403_FORBIDDEN)

    product_id = request.data.get("product_id")
    try:
        product = Product.objects.select_related("artist").get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    if product.is_supporter_only and not has_access(request.user, product.artist, product.profession):
        return Response({"error": "Supporters only"}, status=status.HTTP_403_FORBIDDEN)

    if product.product_type == Product.EVENT_TICKET and fan_already_purchased_product(request.user, product.id):
        return Response({
            "error": "You already have a ticket for this show.",
            "already_purchased": True,
            "product_id": product.id,
        }, status=status.HTTP_409_CONFLICT)

    if demo_mode_allowed():
        from artists.contact_utils import request_bool
        from promotions.redemption import redeem_for_purchase
        from promotions.services import wallet_balance

        redeemed = Decimal("0.00")
        if request_bool(request.data, "apply_discovery_credits", False):
            redeemed, redeem_error = redeem_for_purchase(
                request.user,
                product.price,
                product_title=product.title,
                apply_credits=True,
            )
            if redeem_error:
                return Response({"error": redeem_error}, status=status.HTTP_400_BAD_REQUEST)

        receipt, error = complete_product_purchase(request.user, product, payment_provider="demo")
        if error == "already_purchased":
            return Response({
                "error": "You already have a ticket for this show.",
                "already_purchased": True,
                "product_id": product.id,
            }, status=status.HTTP_409_CONFLICT)
        if error == "sold_out":
            return Response({
                "error": "This show is sold out.",
                "sold_out": True,
                "product_id": product.id,
            }, status=status.HTTP_409_CONFLICT)
        return Response({
            "demo": True,
            "message": (
                f"Purchase recorded with ${redeemed} discovery credit applied."
                if redeemed > Decimal("0.00")
                else "Purchase recorded."
            ),
            "receipt": receipt,
            "discovery_credits_applied": str(redeemed.quantize(Decimal("0.01"))),
            "wallet_balance": str(wallet_balance(request.user).quantize(Decimal("0.01"))),
            **receipt,
        }, status=status.HTTP_201_CREATED)

    if stripe is None:
        return Response({"error": "Stripe package is not installed. Run pip install -r requirements.txt."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    if not settings.STRIPE_SECRET_KEY:
        return Response({"error": "Stripe is not configured. Set STRIPE_SECRET_KEY."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    connect_account_id = connect_account_for_artist(product.artist)
    if not connect_account_id and not settings.DEBUG:
        return Response(
            {"error": "This artist has not completed payout setup yet."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    amount_cents = int(product.price * Decimal("100"))

    try:
        session_kwargs = {
            "mode": "payment",
            "success_url": f"{settings.FRONTEND_URL}/?purchase=success&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{settings.FRONTEND_URL}/?purchase=cancelled",
            "client_reference_id": f"purchase:{request.user.id}:{product.id}",
            "customer_email": request.user.email or None,
            "line_items": [{
                "price_data": {
                    "currency": settings.STRIPE_CURRENCY,
                    "product_data": {
                        "name": product.title,
                        "description": f"From {product.artist.username}",
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }],
            "metadata": {
                "purchase_type": "marketplace",
                "fan_id": str(request.user.id),
                "product_id": str(product.id),
            },
        }
        if connect_account_id:
            _, platform_fee, host_share = ticket_sale_split(product)
            platform_rate = TICKET_PLATFORM_RATE if product.product_type == Product.EVENT_TICKET else MARKETPLACE_PLATFORM_RATE
            session_kwargs["payment_intent_data"] = checkout_payment_intent_data(
                product.price,
                platform_rate,
                connect_account_id,
                host_share=host_share if product.product_type == Product.EVENT_TICKET else None,
            )
        checkout_session = build_checkout_session(**session_kwargs)
    except Exception as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "checkout_url": checkout_session.url,
        "checkout_session_id": checkout_session.id,
    })


@api_view(["POST"])
def create_cart_checkout(request):
    return handle_cart_checkout(request)


@api_view(["POST"])
def create_purchase_checkout(request):
    return handle_purchase_checkout(request)


@api_view(["POST"])
def purchase_product(request):
    return handle_purchase_checkout(request)


@api_view(["GET"])
def my_purchases(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    from spaces.models import SpaceBooking

    results = []
    events = (
        FanJourneyEvent.objects
        .filter(fan=request.user, event_type=FanJourneyEvent.PURCHASE)
        .select_related("artist", "artist__artist_profile")
        .order_by("-occurred_at")[:50]
    )
    seen_product_ids = set()
    for event in events:
        metadata = event.metadata or {}
        product_id = metadata.get("product_id")
        if not product_id or product_id in seen_product_ids:
            continue
        seen_product_ids.add(product_id)

        item = {
            "product_id": product_id,
            "product_title": metadata.get("product_title") or "Purchase",
            "product_type": metadata.get("product_type") or "",
            "amount": metadata.get("amount") or "0.00",
            "purchased_at": event.occurred_at,
            "artist_username": event.artist.username,
            "stage_name": getattr(getattr(event.artist, "artist_profile", None), "stage_name", event.artist.username),
            "show": None,
        }

        if item["product_type"] == Product.EVENT_TICKET:
            booking = (
                SpaceBooking.objects
                .select_related("listing")
                .filter(ticket_product_id=product_id, status=SpaceBooking.CONFIRMED)
                .order_by("starts_at")
                .first()
            )
            from spaces.models import ShowCheckIn

            if booking:
                item["checked_in"] = ShowCheckIn.objects.filter(booking=booking, fan=request.user).exists()
                item["show"] = {
                    "booking_id": booking.id,
                    "starts_at": booking.starts_at,
                    "venue_name": booking.listing.name,
                    "venue_city": booking.listing.city,
                    "checked_in": item["checked_in"],
                }

        results.append(item)

    tickets = [item for item in results if item["product_type"] == Product.EVENT_TICKET]
    return Response({
        "results": results,
        "tickets": tickets,
        "count": len(results),
    })
