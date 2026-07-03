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

# AI training consent values shared by MusicUpload and Product.
# "not_allowed" is the protective default: works are opted out of AI training
# unless the artist explicitly allows it. This is a legal/policy signal, not a
# technical guarantee that public audio can never be analysed.
AI_TRAINING_ALLOWED = "allowed"
AI_TRAINING_NOT_ALLOWED = "not_allowed"
AI_TRAINING_UNKNOWN = "unknown"

AI_TRAINING_CONSENT_CHOICES = [
    (AI_TRAINING_ALLOWED, "Allowed"),
    (AI_TRAINING_NOT_ALLOWED, "Not allowed"),
    (AI_TRAINING_UNKNOWN, "Unknown"),
]


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


class MediaAccessLog(models.Model):
    """One row per protected-file access (stream, download, or preview).

    This is the audit trail behind the anti-scraping foundation: abuse
    detection reads from it and admins can inspect who touched which file.
    """

    STREAM = "stream"
    DOWNLOAD = "download"
    PREVIEW = "preview"

    ACCESS_TYPES = [
        (STREAM, "Stream"),
        (DOWNLOAD, "Download"),
        (PREVIEW, "Preview"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="media_access_logs",
    )
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="media_access_logs_as_artist",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    access_type = models.CharField(max_length=20, choices=ACCESS_TYPES)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=400, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "created_at"]),
            models.Index(fields=["artist", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        return f"MediaAccessLog({self.access_type} {self.content_type_id}:{self.object_id})"


class MediaAbuseFlag(models.Model):
    """Raised when access patterns look like scraping or mass-downloading.

    Heuristic only: flags are for admin review, not automatic punishment.
    """

    TOO_MANY_STREAMS = "too_many_streams"
    TOO_MANY_DOWNLOADS = "too_many_downloads"
    BOT_LIKE_ACCESS = "bot_like_access"
    REPEATED_FULL_TRACK_ACCESS = "repeated_full_track_access"

    FLAG_TYPES = [
        (TOO_MANY_STREAMS, "Too many streams"),
        (TOO_MANY_DOWNLOADS, "Too many downloads"),
        (BOT_LIKE_ACCESS, "Bot-like access"),
        (REPEATED_FULL_TRACK_ACCESS, "Repeated full track access"),
    ]

    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"

    STATUS_CHOICES = [
        (OPEN, "Open"),
        (REVIEWED, "Reviewed"),
        (DISMISSED, "Dismissed"),
    ]

    flag_type = models.CharField(max_length=40, choices=FLAG_TYPES)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="media_abuse_flags",
    )
    artist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="media_abuse_flags_as_artist",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey("content_type", "object_id")

    ip_address = models.GenericIPAddressField(blank=True, null=True)
    detail = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["flag_type", "status"]),
        ]

    def __str__(self):
        return f"MediaAbuseFlag({self.flag_type}) [{self.status}]"
