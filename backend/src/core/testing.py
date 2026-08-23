from django.conf import settings
from django.utils import timezone
from model_bakery import baker
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


def make_published(model, **kwargs):
    kwargs.setdefault("published_at", timezone.now())
    return baker.make(model, **kwargs)


def auth_client(user):
    client = APIClient()
    client.cookies[settings.AUTH_COOKIE["ACCESS_NAME"]] = str(
        RefreshToken.for_user(user).access_token
    )
    return client
