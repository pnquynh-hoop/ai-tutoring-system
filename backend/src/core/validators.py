from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator

MB = 1024 * 1024

MAX_IMAGE_SIZE = 2 * MB
MAX_DOCUMENT_SIZE = 10 * MB
MAX_MATERIAL_SIZE = 100 * MB

# Đuôi file được phép -> content type hợp lệ tương ứng của đuôi đó.
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

# Trình duyệt không đoán được kiểu của .md nên gửi kiểu chung chung.
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


def _extension(file) -> str:
    return Path(getattr(file, "name", "") or "").suffix.lower()


def _content_type(file) -> str:
    return (getattr(file, "content_type", "") or "").split(";")[0].strip().lower()


def _header(file, size: int = 8) -> bytes:
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


def _check_type(file, allowed_types: dict, message: str):
    extension = _extension(file)
    if extension not in allowed_types:
        raise ValidationError(
            f"{message} Định dạng cho phép: %(allowed)s.",
            params={"allowed": ", ".join(sorted(allowed_types))},
        )

    content_type = _content_type(file)
    if content_type not in GENERIC_CONTENT_TYPES | allowed_types[extension]:
        raise ValidationError(
            "Nội dung tệp (%(content_type)s) không khớp với đuôi %(extension)s.",
            params={"content_type": content_type, "extension": extension},
        )

    return extension


def _check_size(file, limit: int, label: str):
    if file.size > limit:
        raise ValidationError(
            "%(label)s không được vượt quá %(limit)dMB (tệp hiện tại %(size).1fMB).",
            params={"label": label, "limit": limit // MB, "size": file.size / MB},
        )


def validate_document_upload(file, max_size: int = MAX_DOCUMENT_SIZE):
    """Tài liệu bài học: chỉ nhận pdf/doc/docx/markdown, tối đa 10MB, không nhận ảnh.

    Bỏ qua giá trị không phải tệp mới tải lên (chuỗi public_id hoặc
    CloudinaryResource của bản ghi cũ) vì chúng không có thuộc tính size.
    """
    if getattr(file, "size", None) is None:
        return file

    extension = _check_type(file, DOCUMENT_TYPES, "Chỉ chấp nhận tệp tài liệu.")
    _check_size(file, max_size, "Tài liệu")

    header = _header(file)
    if header.startswith(IMAGE_SIGNATURES):
        raise ValidationError("Tệp tải lên là hình ảnh, không phải tài liệu.")

    signatures = DOCUMENT_SIGNATURES.get(extension)
    if signatures and not header.startswith(signatures):
        raise ValidationError(
            "Nội dung tệp không phải định dạng %(extension)s hợp lệ.",
            params={"extension": extension},
        )

    return file


def validate_material_upload(file):
    """Tài liệu chung của trung tâm: tối đa 100MB.

    Tệp trên 10MB không đẩy lên Cloudinary mà lưu cục bộ trong backend/data.
    """
    return validate_document_upload(file, MAX_MATERIAL_SIZE)


def validate_image_upload(file):
    """Ảnh của hệ thống: chỉ nhận jpg/jpeg/png/gif/webp, tối đa 2MB."""
    if getattr(file, "size", None) is None:
        return file

    _check_type(file, IMAGE_TYPES, "Chỉ chấp nhận tệp hình ảnh.")
    _check_size(file, MAX_IMAGE_SIZE, "Ảnh")

    if not _header(file).startswith(IMAGE_SIGNATURES):
        raise ValidationError("Nội dung tệp không phải hình ảnh hợp lệ.")

    return file


VIDEO_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "vimeo.com",
    "player.vimeo.com",
}


def validate_video_url(url):
    """Đường dẫn video: bắt buộc http(s) và thuộc các nền tảng được phép."""
    if not url:
        return url

    URLValidator(schemes=["http", "https"])(url)

    if (urlparse(url).hostname or "").lower() not in VIDEO_HOSTS:
        raise ValidationError(
            "Chỉ chấp nhận video từ: %(hosts)s.",
            params={"hosts": ", ".join(sorted(VIDEO_HOSTS))},
        )

    return url


validate_phone = RegexValidator(
    regex=r"^0\d{9}$",
    message="Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.",
)
