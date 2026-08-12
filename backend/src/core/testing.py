from django.conf import settings
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


def make_published(model, **kwargs):
    """Tạo học liệu ở trạng thái đã công khai; để trống là bản nháp, học sinh không thấy."""
    kwargs.setdefault("published_at", timezone.now())
    return baker.make(model, **kwargs)


def auth_client(user) -> APIClient:
    """APIClient đã gắn sẵn cookie JWT của user, khớp CookieJWTAuthentication."""
    client = APIClient()
    client.cookies[settings.AUTH_COOKIE["ACCESS_NAME"]] = str(
        RefreshToken.for_user(user).access_token
    )
    return client
