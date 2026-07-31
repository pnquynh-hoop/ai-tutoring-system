from django.conf import settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


def auth_client(user) -> APIClient:
    """APIClient đã gắn sẵn cookie JWT của user, khớp CookieJWTAuthentication."""
    client = APIClient()
    client.cookies[settings.AUTH_COOKIE["ACCESS_NAME"]] = str(
        RefreshToken.for_user(user).access_token
    )
    return client
