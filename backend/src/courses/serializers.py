from os import read
from attr import field, fields
from rest_framework import serializers

from accounts.serializers import SimpleStudentSerializer
from .models import Chapter, Comment, Course, LearningResource, Lesson, LessonProgress


class StudentCourseSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(
        source="tutor.name", read_only=True, default=None
    )
    progress = serializers.FloatField(read_only=True)

    class Meta:
        fields = ["id", "name", "tutor_name", "progress"]
        model = Course


class CourseDetailSerializer(StudentCourseSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)

    class Meta:
        model = StudentCourseSerializer.Meta.model
        fields = StudentCourseSerializer.Meta.fields + [
            "description",
            "subject_name",
            "grade",
        ]


class LessonTreeSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "is_completed"]


class ChapterTreeSerializer(serializers.ModelSerializer):
    lessons = LessonTreeSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "title", "lessons"]


class CourseTreeSerializer(serializers.ModelSerializer):
    chapters = ChapterTreeSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ["id", "name", "chapters"]


class QuickStatsSerializer(serializers.Serializer):
    ongoing_courses_count = serializers.IntegerField()
    pending_assignments_count = serializers.IntegerField()
    streak = serializers.IntegerField()
    studied_today = serializers.BooleanField()


class LearningResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = ["id", "title", "resource_type", "content", "file_url", "video_url"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file_url:
            try:
                data["file_url"] = instance.file_url.url
            except AttributeError:
                data["file_url"] = str(instance.file_url)
        return data


class LessonDetailSerializer(serializers.ModelSerializer):
    resources = LearningResourceSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "resources"]


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ["id", "student", "lesson", "is_completed", "complete_at"]
        extra_kwargs = {
            "complete_at": {"read_only": True},
            "student": {"required": False},
        }

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = [
            "id",
            "content",
            "is_right",
            "created_by",
            "parent",
            "created_at",
            "lesson",
            "is_active",
        ]
        extra_kwargs = {
            "created_at": {"read_only": True},
            "is_right": {"read_only": True},
            "created_by": {"read_only": True},
            "is_active": {"read_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by"] = SimpleStudentSerializer(instance.created_by).data
        return data

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        request = self.context.get("request")
        data["created_by"] = request.user if request else None
        data["is_active"] = True
        return data
