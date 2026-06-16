from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from artists.models import ArtistProfile

User = get_user_model()


def serialize_user(user):
    artist_profile = getattr(user, "artist_profile", None)

    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "user_type": user.user_type,
        "is_artist": user.user_type == User.ARTIST,
        "artist_profile_id": artist_profile.id if artist_profile else None,
        "favorite_genres": user.favorite_genres,
        "discovery_location": user.discovery_location,
    }


@api_view(['GET'])
def index(request):
    return Response({'app': 'accounts', 'status': 'ready'})


@api_view(["POST"])
def register(request):
    username = (request.data.get("username") or "").strip()
    password = request.data.get("password") or ""
    user_type = request.data.get("user_type") or User.FAN
    display_name = (request.data.get("display_name") or "").strip()
    favorite_genres = (request.data.get("favorite_genres") or "").strip()
    discovery_location = (request.data.get("discovery_location") or request.data.get("city") or "").strip()

    if not username or not password:
        return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    if user_type not in {User.FAN, User.ARTIST}:
        return Response({"error": "Account type must be fan or artist"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.create_user(
            username=username,
            password=password,
            user_type=user_type,
            display_name=display_name,
            favorite_genres=favorite_genres,
            discovery_location=discovery_location,
        )
    except IntegrityError:
        return Response({"error": "Username is already taken"}, status=status.HTTP_400_BAD_REQUEST)

    if user.user_type == User.ARTIST:
        ArtistProfile.objects.get_or_create(
            owner=user,
            defaults={
                "stage_name": request.data.get("stage_name") or display_name or username,
                "genre": request.data.get("genre", ""),
                "city": request.data.get("city", ""),
                "artist_story": request.data.get("artist_story", ""),
                "influences": request.data.get("influences", ""),
            },
        )

    login(request, user)

    return Response({
        "message": "Account created",
        "user": serialize_user(user),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
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

    return Response({
        "message": "Logged in",
        "user": serialize_user(user),
    })


@api_view(["POST"])
def logout_view(request):
    logout(request)
    return Response({"message": "Logged out"})


@ensure_csrf_cookie
@api_view(["GET"])
def current_user(request):
    if not request.user.is_authenticated:
        return Response({"authenticated": False, "user": None})

    return Response({
        "authenticated": True,
        "user": serialize_user(request.user),
    })
