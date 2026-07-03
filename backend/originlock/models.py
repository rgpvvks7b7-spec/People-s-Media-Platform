"""Origin Lock: human-first release approval.

Security model:
- The platform records that an artist *approved* a release. It never stores
  Face ID, Touch ID, fingerprints, face scans, or any biometric data.
- Passkeys rely on device-local user verification (the operating system's
  biometric or PIN prompt). That verification stays on the device and is never
  transmitted to or stored by this platform. Only WebAuthn public-key material
  is stored in ``PasskeyCredential``.
- ``ReleaseApproval.file_hash`` is a SHA-256 digest computed at upload time so a
  release can be detected as tampered with between upload and sealing.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class ReleaseApproval(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    APPROVAL_STATUSES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    PASSKEY = "passkey"
    PASSWORD_FALLBACK = "password_fallback"
    ADMIN = "admin"

    APPROVAL_METHODS = [
        (PASSKEY, "Passkey"),
        (PASSWORD_FALLBACK, "Password fallback"),
        (ADMIN, "Admin"),
    ]

    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="release_approvals",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="sealed_release_approvals",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    file_hash = models.CharField(max_length=64, blank=True)
    file_name = models.CharField(max_length=255, blank=True)

    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUSES, default=PENDING)
    approval_method = models.CharField(max_length=30, choices=APPROVAL_METHODS, blank=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=400, blank=True)

    ai_usage_status = models.CharField(max_length=40, blank=True)
    rights_owner = models.CharField(max_length=200, blank=True)
    writer_credits = models.TextField(blank=True)
    producer_credits = models.TextField(blank=True)
    ai_training_consent = models.BooleanField(default=False)
    origin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                name="unique_release_approval_per_object",
            ),
        ]
        indexes = [
            models.Index(fields=["artist", "approval_status"]),
        ]

    def __str__(self):
        return f"ReleaseApproval({self.content_type_id}:{self.object_id}) [{self.approval_status}]"

    @property
    def is_approved(self):
        return self.approval_status == self.APPROVED


class PasskeyCredential(models.Model):
    """WebAuthn credential. Stores public-key material only, never biometrics."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="passkey_credentials",
    )
    credential_id = models.CharField(max_length=400, unique=True)
    public_key = models.TextField(blank=True)
    sign_count = models.PositiveIntegerField(default=0)
    label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"PasskeyCredential({self.user_id}:{self.label or self.credential_id[:12]})"


class WebAuthnChallenge(models.Model):
    REGISTER = "register"
    AUTHENTICATE = "authenticate"

    PURPOSES = [
        (REGISTER, "Register"),
        (AUTHENTICATE, "Authenticate"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webauthn_challenges",
    )
    challenge = models.CharField(max_length=255)
    purpose = models.CharField(max_length=20, choices=PURPOSES)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"WebAuthnChallenge({self.user_id}:{self.purpose})"
