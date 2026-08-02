from typing import Optional
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken
from .models import StudentProfile, TutorProfile, User


def build_token_claims(user) -> dict:
    group = user.groups.first()
    profile = getattr(user, "studentprofile", None)

    avatar = None
    if user.avatar:
        try:
            avatar = user.avatar.url
        except AttributeError:
            avatar = str(user.avatar)

    return {
        "role": group.name if group else None,
        "full_name": user.full_name,
        "avatar": avatar,
        "grade": profile.grade_level.name if profile and profile.grade_level else None,
    }


class LoginTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token.payload.update(build_token_claims(user))
        return token


class RefreshTokenSerializer(TokenRefreshSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        access = AccessToken(data["access"])
        user = (
            User.objects.select_related("studentprofile__grade_level")
            .filter(pk=access.payload.get(api_settings.USER_ID_CLAIM))
            .first()
        )
        if user:
            access.payload.update(build_token_claims(user))
            data["access"] = str(access)

        return data


class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "avatar"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.avatar:
            try:
                data["avatar"] = instance.avatar.url
            except AttributeError:
                data["avatar"] = str(instance.avatar)
        return data


class StudentProfileSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(
        source="grade_level.name", read_only=True, default=None
    )

    class Meta:
        model = StudentProfile
        fields = ["grade_level", "grade_name", "learning_goals", "academic_level"]


class TutorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorProfile
        fields = ["bio", "qualification", "experience_years", "is_verified"]
        read_only_fields = ["is_verified"]


class TutorSerializer(SimpleUserSerializer):
    tutor_profile = TutorProfileSerializer(
        source="tutorprofile", read_only=True, default=None
    )

    class Meta:
        model = User
        fields = SimpleUserSerializer.Meta.fields + ["tutor_profile"]


class MeSerializer(SimpleUserSerializer):
    role = serializers.SerializerMethodField()
    student_profile = StudentProfileSerializer(
        source="studentprofile", read_only=True, default=None
    )

    def get_role(self, user) -> Optional[str]:
        group = user.groups.first()
        return group.name if group else None

    class Meta:
        model = User
        fields = SimpleUserSerializer.Meta.fields + [
            "role",
            "student_profile",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
        ]


class UpdateMeSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(source="studentprofile", required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "avatar",
            "student_profile",
        ]

    @transaction.atomic
    def update(self, instance, validated_data):
        student_data = validated_data.pop("studentprofile", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if student_data and hasattr(instance, "studentprofile"):
            for field, value in student_data.items():
                setattr(instance.studentprofile, field, value)
            instance.studentprofile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mật khẩu hiện tại không đúng.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Xác nhận mật khẩu không khớp."}
            )

        try:
            validate_password(attrs["new_password"], self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
