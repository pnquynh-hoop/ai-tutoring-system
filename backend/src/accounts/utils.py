from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token):
    if access_token:
        response.set_cookie(
            key=settings.AUTH_COOKIE["ACCESS_NAME"],
            value=access_token,
            httponly=settings.AUTH_COOKIE["HTTP_ONLY"],
            secure=settings.AUTH_COOKIE["SECURE"],
            samesite=settings.AUTH_COOKIE["SAMESITE"],
            path=settings.AUTH_COOKIE["PATH"],
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        )

    if refresh_token:
        response.set_cookie(
            key=settings.AUTH_COOKIE["REFRESH_NAME"],
            value=refresh_token,
            httponly=settings.AUTH_COOKIE["HTTP_ONLY"],
            secure=settings.AUTH_COOKIE["SECURE"],
            samesite=settings.AUTH_COOKIE["SAMESITE"],
            path=settings.AUTH_COOKIE["PATH"],
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )


def remove_tokens(response):
    response.data.pop("access", None)
    response.data.pop("refresh", None)


def clear_auth_cookies(response):
    response.delete_cookie(
        settings.AUTH_COOKIE["ACCESS_NAME"],
        path=settings.AUTH_COOKIE["PATH"],
    )
    response.delete_cookie(
        settings.AUTH_COOKIE["REFRESH_NAME"],
        path=settings.AUTH_COOKIE["PATH"],
    )
