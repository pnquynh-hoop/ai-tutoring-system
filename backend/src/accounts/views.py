from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .utils import set_auth_cookies, clear_auth_cookies, remove_tokens
from django.conf import settings
from .serializers import CustomTokenSerializer, LogoutResponseSerializer
from rest_framework_simplejwt.tokens import AccessToken
from drf_spectacular.utils import extend_schema



class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")

            role = AccessToken(access_token).get("role")
            response.data["role"] = role
            full_name = AccessToken(access_token).get("full_name")
            response.data["full_name"] = full_name

            set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
            )
            # remove_tokens(response)
        return response
    
class RefreshView(TokenRefreshView):

    def post(self, request, *args, **kwargs):
        request.data["refresh"] = request.COOKIES.get(
            settings.AUTH_COOKIE["REFRESH_NAME"]
        )

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")

            set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
            )
            remove_tokens(response)
        return response


class LogoutView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None, 
        responses={200: LogoutResponseSerializer},
    )
    def post(self, request):
        refresh = request.COOKIES.get(settings.AUTH_COOKIE["REFRESH_NAME"])

        if refresh:
            try:
                RefreshToken(refresh).blacklist()

            except Exception:
                pass

        response = Response(
            {"message": "Logout thành công."},
            status=status.HTTP_200_OK,
        )

        clear_auth_cookies(response)
        return response
