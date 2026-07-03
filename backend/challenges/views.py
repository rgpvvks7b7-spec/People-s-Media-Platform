from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .services import get_artist_challenge_board, increment_metric


@api_view(["GET"])
def today(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    return Response(get_artist_challenge_board(request.user))


@api_view(["POST"])
def claim(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

    if request.user.user_type != "artist":
        return Response({"error": "Artist account required"}, status=status.HTTP_403_FORBIDDEN)

    metric = request.data.get("metric")
    if not metric:
        return Response({"error": "metric is required"}, status=status.HTTP_400_BAD_REQUEST)

    completed = increment_metric(request.user, metric)
    board = get_artist_challenge_board(request.user)
    return Response({
        "message": "Challenge progress updated.",
        "completed_count": len(completed),
        "board": board,
    })
