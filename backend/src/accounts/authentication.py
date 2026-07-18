from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE["ACCESS_NAME"])

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
    
class CookieJWTScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.authentication.CookieJWTAuthentication"
    name = "cookieJWTAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.AUTH_COOKIE["ACCESS_NAME"],
        }