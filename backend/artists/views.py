from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ArtistProfile

@api_view(["GET"])
def artist_list(request):
    artists = ArtistProfile.objects.select_related("owner").order_by("-created_at")

    data = []
    for artist in artists:
        data.append({
            "id": artist.id,
            "stage_name": artist.stage_name,
            "genre": artist.genre,
            "city": artist.city,
            "artist_story": artist.artist_story,
            "influences": artist.influences,
            "is_verified": artist.is_verified,
            "owner_id": artist.owner.id,
            "owner_username": artist.owner.username,
            "hero_image": request.build_absolute_uri(artist.hero_image.url) if artist.hero_image else None,

            "show_music": artist.show_music,
            "show_posts": artist.show_posts,
            "show_store": artist.show_store,
            "show_lives": artist.show_lives,
            "show_about": artist.show_about,
        })

    return Response(data)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import ArtistFollow

User = get_user_model()

@api_view(["POST"])
def follow_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")

    try:
        artist = User.objects.get(id=artist_id)
    except User.DoesNotExist:
        return Response({"error": "Artist not found"}, status=status.HTTP_404_NOT_FOUND)

    if artist.user_type != User.ARTIST or not ArtistProfile.objects.filter(owner=artist).exists():
        return Response({"error": "Artist profile not found"}, status=status.HTTP_400_BAD_REQUEST)

    if request.user == artist:
        return Response({"error": "You cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

    ArtistFollow.objects.get_or_create(
        fan=request.user,
        artist=artist
    )

    return Response({"message": "Following"})


@api_view(["POST"])
def unfollow_artist(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    artist_id = request.data.get("artist_id")

    ArtistFollow.objects.filter(
        fan=request.user,
        artist_id=artist_id
    ).delete()

    return Response({"message": "Unfollowed"})


@api_view(["GET"])
def follow_stats(request):

    data = {}

    for user in User.objects.all():

        data[user.username] = {
            "followers": ArtistFollow.objects.filter(
                artist=user
            ).count(),

            "following": ArtistFollow.objects.filter(
                fan=user
            ).count()
        }

    return Response(data)


@api_view(["POST"])
def update_artist_profile(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    artist, _ = ArtistProfile.objects.get_or_create(
        owner=request.user,
        defaults={"stage_name": request.user.display_name or request.user.username},
    )

    artist.stage_name = request.data.get("stage_name", artist.stage_name)
    artist.genre = request.data.get("genre", artist.genre)
    artist.city = request.data.get("city", artist.city)
    artist.artist_story = request.data.get("artist_story", artist.artist_story)
    artist.influences = request.data.get("influences", artist.influences)

    artist.save()

    return Response({
        "message": "Profile updated"
    })


@api_view(["POST"])
def update_page_builder(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != User.ARTIST:
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    artist, _ = ArtistProfile.objects.get_or_create(
        owner=request.user,
        defaults={"stage_name": request.user.display_name or request.user.username},
    )

    artist.show_music = request.data.get("show_music") == "true"
    artist.show_posts = request.data.get("show_posts") == "true"
    artist.show_store = request.data.get("show_store") == "true"
    artist.show_lives = request.data.get("show_lives") == "true"
    artist.show_about = request.data.get("show_about") == "true"

    artist.save()

    return Response({
        "message": "Page layout updated"
    })
