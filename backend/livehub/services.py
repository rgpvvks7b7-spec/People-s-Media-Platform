from subscriptions.models import FanSubscription

from .models import LiveSession


def user_can_join(session, user):
    """Whether ``user`` may listen along (full track + chat) in this session."""
    if user.is_authenticated and user == session.artist:
        return True

    if session.access_mode == LiveSession.SUPPORTERS:
        return bool(user.is_authenticated) and FanSubscription.objects.filter(
            fan=user,
            artist=session.artist,
            active=True,
        ).exists()

    # Every other access mode: any signed-in account can join. Guests get the
    # party page with a signup prompt instead of the stream.
    return bool(user.is_authenticated)


def join_requirement(session, user):
    """Machine-readable reason a viewer cannot join, or "" when they can."""
    if user_can_join(session, user):
        return ""
    if not user.is_authenticated:
        return "account"
    return "supporter"


def party_grants_full_access(track, user):
    """A live listening party temporarily unlocks its featured track.

    While the artist is hosting a party around ``track``, anyone allowed in the
    room can stream the full song — even if it is normally supporter-gated —
    so the room hears the release together.
    """
    sessions = LiveSession.objects.filter(track=track, is_live=True).select_related("artist")
    return any(user_can_join(session, user) for session in sessions)
