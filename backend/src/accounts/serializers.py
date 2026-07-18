from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

class CustomTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.groups.values_list("name", flat=True).first()
        token["full_name"] = user.full_name
        return token
    
class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()