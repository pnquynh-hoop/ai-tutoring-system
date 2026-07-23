from rest_framework import views, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import User
from .utils import set_auth_cookies, clear_auth_cookies, remove_tokens
from django.conf import settings
from .serializers import LogoutResponseSerializer, StudentSerializer
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema



class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")

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

class UserView(viewsets.ViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = StudentSerializer
    
    @action(methods=["get"], detail=False, url_path="me")
    def get_me(self, request):
        return Response(StudentSerializer(request.user).data, status=status.HTTP_200_OK)


