MAX_IMAGE_SIZE = 8 * 1024 * 1024
MAX_VIDEO_SIZE = 25 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}

IMAGE_MAGIC = {
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"RIFF": ".webp",
}


def validate_upload(file_obj, allowed_extensions, max_size, label):
    if not file_obj:
        return None

    name = file_obj.name.lower()
    if not any(name.endswith(ext) for ext in allowed_extensions):
        return f"{label} must be one of: {', '.join(sorted(allowed_extensions))}"

    if file_obj.size > max_size:
        return f"{label} is too large."

    mime_error = validate_image_magic(file_obj, allowed_extensions, label)
    if mime_error:
        return mime_error

    return None


def validate_image_upload(file_obj, label="Image"):
    return validate_upload(file_obj, ALLOWED_IMAGE_EXTENSIONS, MAX_IMAGE_SIZE, label)


def validate_video_upload(file_obj, label="Video"):
    if not file_obj:
        return None

    name = file_obj.name.lower()
    if not any(name.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
        return f"{label} must be one of: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"

    if file_obj.size > MAX_VIDEO_SIZE:
        return f"{label} is too large."

    return None


def validate_image_magic(file_obj, allowed_extensions, label):
    if not allowed_extensions.issubset(ALLOWED_IMAGE_EXTENSIONS):
        return None

    try:
        pos = file_obj.tell()
        header = file_obj.read(12)
        file_obj.seek(pos)
    except (AttributeError, OSError):
        return None

    if not header:
        return f"{label} appears to be empty."

    detected = None
    if header.startswith(b"\xff\xd8\xff"):
        detected = ".jpg"
    elif header.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = ".png"
    elif header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        detected = ".webp"

    if detected and detected not in allowed_extensions:
        return f"{label} content does not match allowed types."

    return None
