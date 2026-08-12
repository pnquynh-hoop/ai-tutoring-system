from rest_framework import serializers
from accounts.serializers import SimpleUserSerializer, TutorSerializer
from core.validators import validate_document_upload, validate_video_url

MAX_RESOURCE_CONTENT_LENGTH = 50000
MAX_COMMENT_LENGTH = 2000
from .models import Chapter, Comment, Course, LearningResource, Lesson


class StudentCourseSerializer(serializers.ModelSerializer):
    tutor_name = serializers.CharField(
        source="tutor.full_name", read_only=True, default=None
    )
    progress = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        fields = ["id", "name", "tutor_name", "progress"]
        model = Course


class TutorCourseSerializer(serializers.ModelSerializer):
    students_count = serializers.IntegerField(read_only=True)
    chapters_count = serializers.IntegerField(read_only=True)
    lessons_count = serializers.IntegerField(read_only=True)
    pending_submission_count = serializers.IntegerField(read_only=True)

    class Meta:
        fields = [
            "id",
            "name",
            "students_count",
            "chapters_count",
            "lessons_count",
            "pending_submission_count",
        ]
        model = Course


class CourseDetailSerializer(StudentCourseSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade = serializers.CharField(source="grade.name", read_only=True)
    tutor = TutorSerializer(read_only=True)

    class Meta:
        model = StudentCourseSerializer.Meta.model
        fields = StudentCourseSerializer.Meta.fields + [
            "description",
            "subject_name",
            "grade",
            "tutor",
        ]


class TutorCourseDetailSerializer(TutorCourseSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    grade = serializers.CharField(source="grade.name", read_only=True)

    class Meta:
        model = TutorCourseSerializer.Meta.model
        fields = TutorCourseSerializer.Meta.fields + [
            "description",
            "subject_name",
            "grade",
        ]


class LessonTreeSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "order", "is_completed"]


class ChapterTreeSerializer(serializers.ModelSerializer):
    lessons = LessonTreeSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "title", "order", "lessons", "assignment"]


class CourseTreeSerializer(serializers.ModelSerializer):
    chapters = ChapterTreeSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ["id", "name", "chapters"]


class StudentQuickStatsSerializer(serializers.Serializer):
    ongoing_courses_count = serializers.IntegerField()
    pending_assignments_count = serializers.IntegerField()
    streak = serializers.IntegerField()
    studied_today = serializers.BooleanField()


class TutorQuickStatsSerializer(serializers.Serializer):
    teaching_course_count = serializers.IntegerField()
    students_count = serializers.IntegerField()
    pending_submission_count = serializers.IntegerField()


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
            "content": {"max_length": MAX_COMMENT_LENGTH},
            "created_at": {"read_only": True},
            "is_right": {"read_only": True},
            "is_active": {"read_only": True},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["created_by"] = SimpleUserSerializer(instance.created_by).data
        return data

    def validate(self, attrs):
        parent = attrs.get("parent")
        lesson = attrs.get("lesson")
        if parent and lesson and parent.lesson_id != lesson.id:
            raise serializers.ValidationError(
                {"parent": "Bình luận cha phải thuộc cùng một bài học."}
            )
        return attrs


class CourseProgressSerializer(serializers.Serializer):
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    progress_percent = serializers.FloatField()


class CourseOverviewSerializer(serializers.Serializer):
    progress = CourseProgressSerializer()
    average_score = serializers.FloatField(allow_null=True)
    pending_assignments_count = serializers.IntegerField()


class TutorStudentStatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)
    completed_lessons = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    progress = serializers.FloatField()
    average_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, coerce_to_string=False
    )


class TutorAssignmentStatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    chapter_title = serializers.CharField()
    due_date = serializers.DateTimeField()
    submitted_count = serializers.IntegerField()
    graded_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    average_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True, coerce_to_string=False
    )


class TutorCourseStatsSerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    students = TutorStudentStatSerializer(many=True)
    assignments = TutorAssignmentStatSerializer(many=True)


class ChapterStatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    order = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    score = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        allow_null=True,
        coerce_to_string=False,
    )
    pending_assignments = serializers.IntegerField()
    first_incomplete_lesson_id = serializers.IntegerField(allow_null=True)


class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = ["id", "course", "title", "order"]


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "chapter", "title", "order"]


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = [
            "id",
            "lesson",
            "title",
            "resource_type",
            "content",
            "file_url",
            "video_url",
        ]
        extra_kwargs = {
            "content": {"max_length": MAX_RESOURCE_CONTENT_LENGTH},
        }

    def validate_file_url(self, file):
        return validate_document_upload(file)

    def validate_video_url(self, url):
        return validate_video_url(url)

    def _value(self, attrs, field):
        if field in attrs:
            return attrs[field]
        return getattr(self.instance, field, None)

    def validate(self, attrs):
        resource_type = self._value(attrs, "resource_type")
        content = self._value(attrs, "content")
        file_url = self._value(attrs, "file_url")
        video_url = self._value(attrs, "video_url")

        if resource_type == LearningResource.ResourceType.VIDEO_URL:
            if not video_url:
                raise serializers.ValidationError(
                    {"video_url": "Tài nguyên dạng video phải có đường dẫn video."}
                )
            if file_url:
                raise serializers.ValidationError(
                    {"file_url": "Tài nguyên dạng video không kèm tệp tài liệu."}
                )
        elif resource_type == LearningResource.ResourceType.PDF_FILE:
            if not file_url:
                raise serializers.ValidationError(
                    {"file_url": "Tài nguyên dạng PDF phải có tệp tài liệu."}
                )
            if video_url:
                raise serializers.ValidationError(
                    {"video_url": "Tài nguyên dạng PDF không kèm đường dẫn video."}
                )
        elif not content and not file_url:
            raise serializers.ValidationError(
                "Tài nguyên phải có nội dung văn bản hoặc tệp tài liệu."
            )

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.file_url:
            try:
                data["file_url"] = instance.file_url.url
            except AttributeError:
                data["file_url"] = str(instance.file_url)
        return data
