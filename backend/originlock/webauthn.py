"""WebAuthn/passkey placeholder helpers.

This is a passkey-ready scaffold. It issues and tracks challenges and validates
the *shape* of a WebAuthn assertion so the frontend can be wired against real
``navigator.credentials`` calls. Cryptographic signature verification is
intentionally deferred to a follow-up (see the plan's non-goals).

Nothing here touches biometric data: passkeys verify the user on-device and the
platform only ever sees public-key material and opaque challenge strings.
"""

import base64
import os

from django.utils import timezone

from .models import PasskeyCredential, WebAuthnChallenge

CHALLENGE_TTL_SECONDS = 300


def generate_challenge():
    return base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("=")


def issue_challenge(user, purpose):
    challenge = generate_challenge()
    WebAuthnChallenge.objects.filter(user=user, purpose=purpose).delete()
    WebAuthnChallenge.objects.create(
        user=user,
        challenge=challenge,
        purpose=purpose,
        expires_at=timezone.now() + timezone.timedelta(seconds=CHALLENGE_TTL_SECONDS),
    )
    return challenge


def consume_challenge(user, purpose, challenge):
    if not challenge:
        return False
    now = timezone.now()
    record = (
        WebAuthnChallenge.objects
        .filter(user=user, purpose=purpose, challenge=challenge)
        .first()
    )
    if not record:
        return False
    is_valid = record.expires_at >= now
    record.delete()
    return is_valid


def verify_assertion(user, payload):
    """Validate a WebAuthn assertion stub.

    Confirms the challenge was one we issued and that the presented credential
    belongs to the user. Real signature verification is wired in a follow-up.
    """
    payload = payload or {}
    challenge = payload.get("challenge")
    credential_id = payload.get("credential_id")

    if not consume_challenge(user, WebAuthnChallenge.AUTHENTICATE, challenge):
        return None

    credential = PasskeyCredential.objects.filter(
        user=user,
        credential_id=credential_id,
    ).first()
    if not credential:
        return None

    credential.last_used_at = timezone.now()
    credential.save(update_fields=["last_used_at"])
    return credential
