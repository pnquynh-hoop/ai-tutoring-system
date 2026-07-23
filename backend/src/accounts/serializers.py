from typing import Optional
from rest_framework import serializers
from .models import User

class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()

class SimpleStudentSerializer(serializers.ModelSerializer):
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

class StudentSerializer(SimpleStudentSerializer):
    role = serializers.SerializerMethodField()
    grade = serializers.CharField(source="studentprofile.grade_level.name", read_only=True)
    
    def get_role(self, user) -> Optional[str]:
        group = user.groups.first()
        return group.name if group else None

    class Meta:
        fields = SimpleStudentSerializer.Meta.fields + ["role", "grade"]
        model = User
    

    