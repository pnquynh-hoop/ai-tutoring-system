from pathlib import Path
from urllib.parse import urlparse
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

MB = 1024 * 1024

MAX_IMAGE_SIZE = 2 * MB
MAX_DOCUMENT_SIZE = 10 * MB
MAX_MATERIAL_SIZE = 100 * MB

DOCUMENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".doc": {"application/msword"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    },
    ".md": {"text/markdown", "text/x-markdown", "text/plain"},
    ".markdown": {"text/markdown", "text/x-markdown", "text/plain"},
}

IMAGE_TYPES = {
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
    ".gif": {"image/gif"},
    ".webp": {"image/webp"},
}

GENERIC_CONTENT_TYPES = {"", "application/octet-stream", "binary/octet-stream"}

IMAGE_SIGNATURES = (
    b"\xff\xd8\xff",
    b"\x89PNG\r\n\x1a\n",
    b"GIF87a",
    b"GIF89a",
    b"RIFF",
    b"BM",
)

DOCUMENT_SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".docx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0",),
}


def get_extension(file):
    return Path(getattr(file, "name", "") or "").suffix.lower()


def get_content_type(file):
    return (getattr(file, "content_type", "") or "").split(";")[0].strip().lower()


def read_header(file, size=8):
    try:
        file.seek(0)
        header = file.read(size)
    except (AttributeError, OSError):
        return b""
    finally:
        try:
            file.seek(0)
        except (AttributeError, OSError):
            pass
    return header


def check_type(file, allowed_types, message):
    extension = get_extension(file)
    if extension not in allowed_types:
        raise ValidationError(
            f"{message} Định dạng cho phép: %(allowed)s.",
            params={"allowed": ", ".join(sorted(allowed_types))},
        )

    content_type = get_content_type(file)
    if content_type not in GENERIC_CONTENT_TYPES | allowed_types[extension]:
        raise ValidationError(
            "Nội dung tệp (%(content_type)s) không khớp với phần mở rộng %(extension)s.",
            params={"content_type": content_type, "extension": extension},
        )
    return extension


def check_size(file, limit, label):
    if file.size > limit:
        raise ValidationError(
            "%(label)s không được vượt quá %(limit)dMB (tệp hiện tại %(size).1fMB).",
            params={"label": label, "limit": limit // MB, "size": file.size / MB},
        )


def validate_document_upload(file, max_size=MAX_DOCUMENT_SIZE):
    if getattr(file, "size", None) is None:
        return file

    extension = check_type(file, DOCUMENT_TYPES, "Chỉ chấp nhận tệp tài liệu.")
    check_size(file, max_size, "Tài liệu")

    header = read_header(file)
    if header.startswith(IMAGE_SIGNATURES):
        raise ValidationError("Tệp tải lên là hình ảnh, không phải tài liệu hợp lệ.")

    signatures = DOCUMENT_SIGNATURES.get(extension)
    if signatures and not header.startswith(signatures):
        raise ValidationError(
            "Nội dung tệp không phải định dạng %(extension)s hợp lệ.",
            params={"extension": extension},
        )
    return file


def validate_image_upload(file):
    if getattr(file, "size", None) is None:
        return file

    check_type(file, IMAGE_TYPES, "Chỉ chấp nhận tệp hình ảnh.")
    check_size(file, MAX_IMAGE_SIZE, "Ảnh")

    if not read_header(file).startswith(IMAGE_SIGNATURES):
        raise ValidationError("Nội dung tệp không phải hình ảnh hợp lệ.")

    return file


VIDEO_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}


def validate_video_url(url):
    if not url:
        return url

    URLValidator(schemes=["http", "https"])(url)

    if (urlparse(url).hostname or "") not in VIDEO_HOSTS:
        raise ValidationError(
            "Chỉ chấp nhận video từ: %(hosts)s.",
            params={"hosts": ", ".join(sorted(VIDEO_HOSTS))},
        )
    return url
