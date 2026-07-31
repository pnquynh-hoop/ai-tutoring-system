from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import StudentProfile, User
from .serializers import (
    ChangePasswordSerializer,
    ChoiceSerializer,
    LoginTokenSerializer,
    LogoutResponseSerializer,
    MeSerializer,
    RefreshTokenSerializer,
    UpdateMeSerializer,
)
from .utils import clear_auth_cookies, remove_tokens, set_auth_cookies


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginTokenSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            set_auth_cookies(
                response,
                access_token=response.data.get("access"),
                refresh_token=response.data.get("refresh"),
            )
            remove_tokens(response)
        return response


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RefreshTokenSerializer

    def post(self, request, *args, **kwargs):
        request.data["refresh"] = request.COOKIES.get(
            settings.AUTH_COOKIE["REFRESH_NAME"]
        )

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            set_auth_cookies(
                response,
                access_token=response.data.get("access"),
                refresh_token=response.data.get("refresh"),
            )
            remove_tokens(response)
        return response


class LogoutView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=None,
        responses={200: LogoutResponseSerializer},
    )
    def post(self, request):
        refresh = request.COOKIES.get(settings.AUTH_COOKIE["REFRESH_NAME"])

        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass

        response = Response(
            {"message": "Logout thành công."},
            status=status.HTTP_200_OK,
        )

        clear_auth_cookies(response)
        return response


class UserView(viewsets.ViewSet, generics.GenericAPIView):
    queryset = User.objects.filter(is_active=True)
    serializer_class = MeSerializer

    def get_serializer_class(self):
        if self.action == "change_password":
            return ChangePasswordSerializer
        if self.action == "get_me" and self.request.method == "PATCH":
            return UpdateMeSerializer
        return MeSerializer

    @extend_schema(responses=MeSerializer)
    @action(methods=["get", "patch"], detail=False, url_path="me")
    def get_me(self, request):
        if request.method == "PATCH":
            serializer = self.get_serializer(
                request.user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(
            MeSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses=ChoiceSerializer(many=True))
    @action(
        methods=["get"],
        detail=False,
        url_path="academic-levels",
    )
    def academic_levels(self, request):
        return Response(
            [
                {"value": value, "label": label}
                for value, label in StudentProfile.AcademicLevel.choices
            ],
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=ChangePasswordSerializer, responses={200: LogoutResponseSerializer}
    )
    @action(methods=["post"], detail=False, url_path="change-password")
    def change_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Đổi mật khẩu thành công."}, status=status.HTTP_200_OK
        )
