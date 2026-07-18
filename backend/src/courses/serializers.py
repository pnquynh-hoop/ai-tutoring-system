from rest_framework import serializers
from .models import Course

class CourseSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(source="tutor.name", read_only=True)

    class Meta:
        fields = ["id", "name", "tutor_name"]
        model = Course
