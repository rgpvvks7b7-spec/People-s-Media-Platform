from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from .models import Product
from subscriptions.models import FanSubscription

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


def has_access(user, artist):
    if user.is_authenticated and user == artist:
        return True

    if not user.is_authenticated:
        return False

    return FanSubscription.objects.filter(
        fan=user,
        artist=artist,
        active=True,
    ).exists()

@api_view(["GET"])
def product_list(request):
    products = Product.objects.select_related("artist").filter(is_active=True).order_by("-created_at")

    data = []
    for product in products:
        can_access = (not product.is_supporter_only) or has_access(request.user, product.artist)
        data.append({
            "id": product.id,
            "artist_id": product.artist.id,
            "artist_username": product.artist.username,
            "product_type": product.product_type,
            "title": product.title,
            "description": product.description,
            "price": str(product.price),
            "image": request.build_absolute_uri(product.image.url) if product.image else None,
            "preview_audio": request.build_absolute_uri(product.preview_audio.url) if product.preview_audio and can_access else None,
            "product_file": request.build_absolute_uri(product.product_file.url) if product.product_file and can_access else None,
            "stock_quantity": product.stock_quantity,
            "sizes": product.sizes,
            "shipping_required": product.shipping_required,
            "is_supporter_only": product.is_supporter_only,
            "can_access": can_access,
            "access_message": "" if can_access else "Supporters only",
            "bpm": product.bpm,
            "music_key": product.music_key,
            "license_type": product.license_type,
            "created_at": product.created_at,
        })

    return Response(data)


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

    product = Product.objects.create(
        artist=request.user,
        product_type=request.data.get("product_type", Product.MERCH),
        title=request.data.get("title", "Untitled Product"),
        description=request.data.get("description", ""),
        price=request.data.get("price", "1.00"),
        image=image,
        preview_audio=preview_audio,
        product_file=product_file,
        stock_quantity=request.data.get("stock_quantity", 0) or 0,
        sizes=request.data.get("sizes", ""),
        shipping_required=request.data.get("shipping_required") == "true",
        is_supporter_only=request.data.get("is_supporter_only") == "true",
        bpm=request.data.get("bpm") or None,
        music_key=request.data.get("music_key", ""),
        license_type=request.data.get("license_type", ""),
    )

    return Response({
        "message": "Product created",
        "id": product.id,
        "title": product.title,
        "product_type": product.product_type,
        "price": str(product.price),
    }, status=status.HTTP_201_CREATED)
